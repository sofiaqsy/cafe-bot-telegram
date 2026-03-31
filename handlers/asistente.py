"""
AI assistant handler.
Listens to free-text messages and uses Groq/Gemini to understand the user's intent,
then guides them through confirmation before saving the record.
"""
import logging
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)

from config import GROQ_API_KEY, GEMINI_API_KEY
from utils.ai import parse_message
from utils.sheets import append_data as sheets_append, buscar_proveedor
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.sheets import generate_unique_id
from utils.formatters import formatear_precio

logger = logging.getLogger(__name__)

# Conversation states
CONFIRMAR = 0
PEDIR_CAMPO = 1
CONFIRMAR_PROVEEDOR = 2

# Required fields per action
REQUIRED_FIELDS = {
    "compra":   ["tipo_cafe", "proveedor", "cantidad", "precio"],
    "gasto":    ["concepto", "monto", "categoria"],
    "adelanto": ["proveedor", "monto"],
}

TIPOS_CAFE = ["CEREZO", "MOTE", "PERGAMINO"]
CATEGORIAS_GASTO = ["Operativo", "Mantenimiento", "Transporte", "Personal", "Insumos", "Servicios", "Otro"]

# Human-readable question for each missing field
FIELD_QUESTIONS = {
    "tipo_cafe":  "¿Tipo de café?\n\nOpciones: CEREZO, MOTE, PERGAMINO",
    "proveedor":  "¿Nombre del proveedor?",
    "cantidad":   "¿Cantidad en kg? (solo el número)",
    "precio":     "¿Precio por kg en S/? (solo el número)",
    "concepto":   "¿Cuál es el concepto o descripción del gasto?",
    "monto":      "¿Cuánto es el monto en S/? (solo el número)",
    "categoria":  "¿Categoría del gasto?\n\nOpciones: Operativo, Mantenimiento, Transporte, Personal, Insumos, Servicios, Otro",
}


def _build_summary(accion: str, datos: dict) -> str:
    """Build a human-readable summary of the operation."""
    if accion == "compra":
        total = round(float(datos.get("cantidad", 0)) * float(datos.get("precio", 0)), 2)
        return (
            f"📦 *RESUMEN DE COMPRA*\n\n"
            f"Tipo de café: {datos.get('tipo_cafe')}\n"
            f"Proveedor: {datos.get('proveedor')}\n"
            f"Cantidad: {datos.get('cantidad')} kg\n"
            f"Precio: {formatear_precio(datos.get('precio'))} / kg\n"
            f"Total: {formatear_precio(total)}\n\n"
            "¿Confirmas? (Sí / No)"
        )
    elif accion == "gasto":
        proveedor_line = f"Proveedor: {datos.get('proveedor')}\n" if datos.get("proveedor") else ""
        return (
            f"💸 *RESUMEN DE GASTO*\n\n"
            f"Concepto: {datos.get('concepto')}\n"
            f"Monto: {formatear_precio(datos.get('monto'))}\n"
            f"Categoría: {datos.get('categoria')}\n"
            f"{proveedor_line}\n"
            "¿Confirmas? (Sí / No)"
        )
    elif accion == "adelanto":
        return (
            f"💵 *RESUMEN DE ADELANTO*\n\n"
            f"Proveedor: {datos.get('proveedor')}\n"
            f"Monto: {formatear_precio(datos.get('monto'))}\n\n"
            "¿Confirmas? (Sí / No)"
        )
    return "¿Confirmas? (Sí / No)"


def _save_compra(datos: dict, username: str) -> bool:
    now = get_now_peru()
    fecha = format_date_for_sheets(now.strftime("%Y-%m-%d %H:%M"))
    cantidad = float(datos.get("cantidad", 0))
    precio = float(datos.get("precio", 0))
    record = {
        "id": generate_unique_id(),
        "fecha": fecha,
        "tipo_cafe": datos.get("tipo_cafe", ""),
        "proveedor": datos.get("proveedor", ""),
        "cantidad": cantidad,
        "precio": precio,
        "preciototal": round(cantidad * precio, 2),
        "registrado_por": username,
        "notas": "Registrado por asistente IA",
    }
    return sheets_append("compras", record)


def _save_gasto(datos: dict, username: str) -> bool:
    now = get_now_peru()
    descripcion = datos.get("concepto", "")
    # Append account number to descripcion since gastos sheet has no notas column
    if datos.get("notas"):
        descripcion = f"{descripcion} | {datos['notas']}"
    record = {
        "fecha": now.strftime("%Y-%m-%d %H:%M:%S"),
        "descripcion": descripcion,
        "monto": float(datos.get("monto", 0)),
        "categoria": datos.get("categoria", ""),
        "registrado_por": username,
    }
    return sheets_append("gastos", record)


def _save_adelanto(datos: dict, username: str) -> bool:
    now = get_now_peru()
    monto = float(datos.get("monto", 0))
    record = {
        "fecha": format_date_for_sheets(now.strftime("%Y-%m-%d")),
        "hora": now.strftime("%H:%M:%S"),
        "proveedor": datos.get("proveedor", ""),
        "monto": monto,
        "saldo_restante": monto,
        "notas": "Registrado por asistente IA",
        "registrado_por": username,
    }
    return sheets_append("adelantos", record)


def _validate_field(field: str, value: str) -> tuple[bool, str]:
    """
    Validate a user-provided field value.
    Returns (is_valid, normalized_value_or_error_message).
    """
    value = value.strip()

    if field == "tipo_cafe":
        normalized = value.upper()
        if normalized in TIPOS_CAFE:
            return True, normalized
        return False, f"Tipo inválido. Elige: CEREZO, MOTE o PERGAMINO"

    if field in ("cantidad", "precio", "monto"):
        try:
            num = float(value.replace(",", "."))
            if num <= 0:
                return False, "El valor debe ser mayor a cero."
            return True, num
        except ValueError:
            return False, "Ingresa un número válido."

    if field == "categoria":
        for cat in CATEGORIAS_GASTO:
            if value.lower() == cat.lower():
                return True, cat
        # Try partial match
        for cat in CATEGORIAS_GASTO:
            if value.lower() in cat.lower():
                return True, cat
        return False, f"Categoría inválida. Elige: {', '.join(CATEGORIAS_GASTO)}"

    # proveedor, concepto: any non-empty string
    if not value:
        return False, "Este campo no puede estar vacío."
    return True, value


async def ai_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: process free-text message with AI."""
    user = update.effective_user
    user_message = update.message.text.strip()

    logger.info(f"[ASISTENTE] Mensaje recibido de {user.id} (@{user.username}): '{user_message}'")
    logger.info(f"[ASISTENTE] GROQ_API_KEY configurada: {'Sí' if GROQ_API_KEY else 'NO ❌'}")
    logger.info(f"[ASISTENTE] GEMINI_API_KEY configurada: {'Sí' if GEMINI_API_KEY else 'NO ❌'}")

    SALUDOS = {"hola", "holi", "hey", "buenas", "hi", "hello", "khe", "ke", "qué", "que", "ola"}
    if len(user_message) < 5 or user_message.lower() in SALUDOS:
        logger.info(f"[ASISTENTE] Saludo o mensaje corto — respondiendo con menú.")
        await update.message.reply_text(
            f"¡Hola! 👋 ¿Qué deseas registrar hoy?\n\n"
            "Puedes escribirme con tus propias palabras, por ejemplo:\n"
            "• _\"Compré 50 kg de cerezo a Juan a 3 soles\"_\n"
            "• _\"Gasté 200 soles en combustible\"_\n"
            "• _\"Le di un adelanto de 500 a María\"_\n\n"
            "O usa los comandos directos:\n"
            "/compra · /gasto · /adelanto · /compra_mixta",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    await update.message.reply_text("🤖 Analizando tu mensaje...")

    logger.info(f"[ASISTENTE] Llamando a parse_message...")
    result = parse_message(user_message, GROQ_API_KEY, GEMINI_API_KEY)
    logger.info(f"[ASISTENTE] Resultado IA: {result}")
    accion = result.get("accion", "desconocido")

    if accion == "desconocido" or not result.get("entendido"):
        await update.message.reply_text(
            f"❓ No entendí qué quieres registrar.\n\n"
            f"{result.get('confirmacion', '')}\n\n"
            "Usa los comandos directos:\n"
            "/compra · /gasto · /adelanto",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    # Store AI result in user context
    context.user_data["ai_accion"] = accion
    context.user_data["ai_datos"] = result.get("datos", {})
    faltante = [f for f in result.get("faltante", []) if f in REQUIRED_FIELDS.get(accion, [])]
    context.user_data["ai_faltante"] = faltante

    if not faltante:
        return await _mostrar_confirmacion(update, context)

    # Ask for the first missing field
    campo = faltante[0]
    await update.message.reply_text(
        f"✅ Entendí: {result.get('confirmacion', '')}\n\n"
        f"Necesito un dato más:\n{FIELD_QUESTIONS[campo]}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return PEDIR_CAMPO


async def pedir_campo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive the value for the current missing field, ask next one or confirm."""
    faltante = context.user_data.get("ai_faltante", [])
    if not faltante:
        # Nothing left to ask — go to confirmation
        return await _mostrar_confirmacion(update, context)

    campo = faltante[0]
    value_raw = update.message.text.strip()
    is_valid, value_or_error = _validate_field(campo, value_raw)

    if not is_valid:
        await update.message.reply_text(
            f"⚠️ {value_or_error}\n\n{FIELD_QUESTIONS[campo]}",
            reply_markup=ReplyKeyboardRemove(),
        )
        return PEDIR_CAMPO

    # Save valid value
    context.user_data["ai_datos"][campo] = value_or_error
    context.user_data["ai_faltante"] = faltante[1:]

    if context.user_data["ai_faltante"]:
        # Ask next missing field
        siguiente = context.user_data["ai_faltante"][0]
        await update.message.reply_text(
            FIELD_QUESTIONS[siguiente],
            reply_markup=ReplyKeyboardRemove(),
        )
        return PEDIR_CAMPO

    return await _mostrar_confirmacion(update, context)


async def _mostrar_confirmacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check provider account, then show final summary with inline buttons."""
    accion = context.user_data["ai_accion"]
    datos = context.user_data["ai_datos"]

    # Check if this action has a provider and the provider exists in the sheet
    # For gastos, also try matching the concepto if proveedor is not explicitly set
    nombre_proveedor = datos.get("proveedor")
    if not nombre_proveedor and accion == "gasto":
        nombre_proveedor = datos.get("concepto")
    if nombre_proveedor and accion in ("compra", "adelanto", "gasto"):
        proveedor = buscar_proveedor(nombre_proveedor)
        if proveedor:
            logger.info(f"[ASISTENTE] Proveedor encontrado: {proveedor}")
            if not proveedor.get("numero_cuenta"):
                logger.warning(f"[ASISTENTE] Proveedor '{nombre_proveedor}' encontrado pero sin 'numero_cuenta'. Columnas: {list(proveedor.keys())}")
        if proveedor and proveedor.get("numero_cuenta"):
            context.user_data["ai_proveedor_info"] = proveedor
            banco = proveedor.get("banco", "—")
            numero = proveedor.get("numero_cuenta", "—")
            tipo = proveedor.get("tipo_cuenta", "—")
            texto = (
                f"🏦 *Cuenta del proveedor encontrada*\n\n"
                f"Proveedor: {proveedor.get('nombre')}\n"
                f"Banco: {banco}\n"
                f"Número de cuenta: `{numero}`\n"
                f"Tipo: {tipo}\n\n"
                "¿Es esta la cuenta correcta?"
            )
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Sí, continuar", callback_data="prov_ok"),
                InlineKeyboardButton("❌ No, cancelar", callback_data="prov_cancel"),
            ]])
            await update.message.reply_text(texto, parse_mode="Markdown", reply_markup=keyboard)
            return CONFIRMAR_PROVEEDOR

    # No provider info — go straight to final confirmation
    return await _mostrar_resumen_final(update.message, context)


async def _mostrar_resumen_final(message, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the operation summary and ask for final confirmation."""
    accion = context.user_data["ai_accion"]
    datos = context.user_data["ai_datos"]

    # Attach account number to notas if provider info was confirmed
    proveedor_info = context.user_data.get("ai_proveedor_info")
    if proveedor_info and proveedor_info.get("numero_cuenta"):
        cuenta = proveedor_info["numero_cuenta"]
        banco = proveedor_info.get("banco", "")
        nota_cuenta = f"Cuenta {banco}: {cuenta}".strip()
        datos["notas"] = nota_cuenta
        context.user_data["ai_datos"] = datos

    summary = _build_summary(accion, datos)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirmar", callback_data="ai_confirmar"),
        InlineKeyboardButton("❌ Cancelar", callback_data="ai_cancelar"),
    ]])
    await message.reply_text(summary, parse_mode="Markdown", reply_markup=keyboard)
    return CONFIRMAR


async def confirmar_proveedor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the provider account confirmation step."""
    query = update.callback_query
    await query.answer()

    if query.data == "prov_cancel":
        await query.edit_message_text("❌ Operación cancelada.")
        context.user_data.clear()
        return ConversationHandler.END

    # Provider confirmed — show final summary
    await query.edit_message_text("✅ Cuenta confirmada.")
    return await _mostrar_resumen_final(query.message, context)


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save the record when user taps Confirmar button."""
    query = update.callback_query
    await query.answer()

    accion = context.user_data.get("ai_accion")
    datos = context.user_data.get("ai_datos", {})
    username = update.effective_user.username or update.effective_user.first_name

    if query.data == "ai_cancelar":
        await query.edit_message_text("❌ Operación cancelada.")
        context.user_data.clear()
        return ConversationHandler.END

    try:
        if accion == "compra":
            ok = _save_compra(datos, username)
        elif accion == "gasto":
            ok = _save_gasto(datos, username)
        elif accion == "adelanto":
            ok = _save_adelanto(datos, username)
        else:
            ok = False

        if ok:
            await query.edit_message_text(
                "✅ ¡Registrado correctamente!\n\n"
                "Puedes seguir registrando con un nuevo mensaje o usando los comandos."
            )
        else:
            await query.edit_message_text(
                "❌ Error al guardar. Intenta nuevamente o usa el comando directo."
            )
    except Exception as e:
        logger.error(f"Error saving AI record: {e}")
        await query.edit_message_text("❌ Error al guardar. Intenta nuevamente.")

    context.user_data.clear()
    return ConversationHandler.END


async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the AI assistant conversation."""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelado.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def register_asistente_handlers(application):
    """Register the AI assistant handler (low priority — runs after all other handlers)."""
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, ai_entry)],
        states={
            CONFIRMAR_PROVEEDOR: [CallbackQueryHandler(confirmar_proveedor, pattern=r"^prov_(ok|cancel)$")],
            CONFIRMAR:           [CallbackQueryHandler(confirmar, pattern=r"^ai_(confirmar|cancelar)$")],
            PEDIR_CAMPO:         [MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_campo)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        per_message=False,
    )
    application.add_handler(conv_handler)
    logger.info("✅ Asistente IA registrado en grupo 0 (último, no interferirá con otros handlers)")
