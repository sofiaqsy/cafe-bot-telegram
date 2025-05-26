import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from utils.helpers import get_now_peru, format_date_for_sheets, safe_float
from utils.sheets import append_data as append_sheets, generate_unique_id

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
MONTO, ORIGEN, DESTINO, CONCEPTO, NOTAS, CONFIRMAR = range(6)

# Datos temporales
datos_capitalizacion = {}

# Opciones predefinidas
ORIGENES = ["Fondos personales", "Préstamo", "Inversión externa", "Ganancias reinvertidas", "Otro"]
DESTINOS = ["Compra de café", "Gastos operativos", "Equipamiento", "Expansión", "Otro"]

async def capitalizacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de capitalización"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} inició comando /capitalizacion")
    
    # Inicializar datos para este usuario
    datos_capitalizacion[user_id] = {
        "registrado_por": update.effective_user.username or update.effective_user.first_name
    }
    
    await update.message.reply_text(
        "💰 *REGISTRO DE CAPITALIZACIÓN*\n\n"
        "Vamos a registrar un nuevo ingreso de capital.\n\n"
        "Por favor, ingresa el monto a capitalizar (solo el número):",
        parse_mode="Markdown"
    )
    
    return MONTO

async def monto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el monto de capitalización y solicita el origen"""
    user_id = update.effective_user.id
    text = update.message.text
    
    try:
        monto = safe_float(text)
        if monto <= 0:
            await update.message.reply_text(
                "⚠️ El monto debe ser mayor que cero.\n\n"
                "Por favor, ingresa un monto válido:"
            )
            return MONTO
        
        # Guardar el monto
        datos_capitalizacion[user_id]["monto"] = monto
        
        # Crear teclado con opciones de origen
        keyboard = [[origen] for origen in ORIGENES]
        markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Monto registrado: S/ {monto:.2f}\n\n"
            "Por favor, selecciona el *origen* de los fondos:",
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        return ORIGEN
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un monto válido (solo números):"
        )
        return MONTO

async def origen_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el origen de los fondos y solicita el destino"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Si eligió "Otro", solicitar que especifique
    if text == "Otro":
        await update.message.reply_text(
            "Por favor, especifica el origen de los fondos:",
            reply_markup=ReplyKeyboardRemove()
        )
        datos_capitalizacion[user_id]["origen_otro"] = True
        return ORIGEN
    elif "origen_otro" in datos_capitalizacion[user_id]:
        # Es la respuesta después de elegir "Otro"
        del datos_capitalizacion[user_id]["origen_otro"]
    
    # Guardar el origen
    datos_capitalizacion[user_id]["origen"] = text
    
    # Crear teclado con opciones de destino
    keyboard = [[destino] for destino in DESTINOS]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Origen registrado: {text}\n\n"
        "Por favor, selecciona el *destino* de los fondos:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
    return DESTINO

async def destino_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el destino de los fondos y solicita el concepto"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Si eligió "Otro", solicitar que especifique
    if text == "Otro":
        await update.message.reply_text(
            "Por favor, especifica el destino de los fondos:",
            reply_markup=ReplyKeyboardRemove()
        )
        datos_capitalizacion[user_id]["destino_otro"] = True
        return DESTINO
    elif "destino_otro" in datos_capitalizacion[user_id]:
        # Es la respuesta después de elegir "Otro"
        del datos_capitalizacion[user_id]["destino_otro"]
    
    # Guardar el destino
    datos_capitalizacion[user_id]["destino"] = text
    
    await update.message.reply_text(
        f"Destino registrado: {text}\n\n"
        "Por favor, ingresa un concepto o descripción breve:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return CONCEPTO

async def concepto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el concepto y solicita notas adicionales"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Guardar el concepto
    datos_capitalizacion[user_id]["concepto"] = text
    
    # Crear teclado con opciones rápidas
    keyboard = [["Sin notas adicionales"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Concepto registrado: {text}\n\n"
        "Por favor, ingresa notas adicionales (opcional):",
        reply_markup=markup
    )
    
    return NOTAS

async def notas_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa las notas y muestra resumen para confirmar"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Guardar las notas
    if text == "Sin notas adicionales":
        datos_capitalizacion[user_id]["notas"] = ""
    else:
        datos_capitalizacion[user_id]["notas"] = text
    
    # Generar ID único
    datos_capitalizacion[user_id]["id"] = generate_unique_id("CAP")
    
    # Obtener fecha y hora actual
    now = get_now_peru()
    datos_capitalizacion[user_id]["fecha"] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # Crear teclado para confirmar
    keyboard = [["✅ Confirmar", "❌ Cancelar"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Preparar resumen
    resumen = (
        f"📝 *RESUMEN DE CAPITALIZACIÓN*\n\n"
        f"ID: `{datos_capitalizacion[user_id]['id']}`\n"
        f"Fecha: {datos_capitalizacion[user_id]['fecha']}\n"
        f"Monto: S/ {datos_capitalizacion[user_id]['monto']:.2f}\n"
        f"Origen: {datos_capitalizacion[user_id]['origen']}\n"
        f"Destino: {datos_capitalizacion[user_id]['destino']}\n"
        f"Concepto: {datos_capitalizacion[user_id]['concepto']}\n"
    )
    
    if datos_capitalizacion[user_id]["notas"]:
        resumen += f"Notas: {datos_capitalizacion[user_id]['notas']}\n"
    
    resumen += "\n¿Deseas confirmar esta capitalización?"
    
    await update.message.reply_text(
        resumen,
        reply_markup=markup,
        parse_mode="Markdown"
    )
    
    return CONFIRMAR

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra la capitalización"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "❌ Cancelar":
        # Limpiar datos
        if user_id in datos_capitalizacion:
            del datos_capitalizacion[user_id]
        
        await update.message.reply_text(
            "Operación cancelada. No se ha registrado ninguna capitalización.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END
    
    if text != "✅ Confirmar":
        # Si no es una respuesta válida
        keyboard = [["✅ Confirmar", "❌ Cancelar"]]
        markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "Por favor, selecciona una opción válida: Confirmar o Cancelar",
            reply_markup=markup
        )
        
        return CONFIRMAR
    
    # Obtener datos
    datos = datos_capitalizacion[user_id]
    
    try:
        # Preparar datos para Google Sheets
        row = [
            datos["id"],
            format_date_for_sheets(datos["fecha"]),
            datos["monto"],
            datos["origen"],
            datos["destino"],
            datos["concepto"],
            datos["registrado_por"],
            datos["notas"]
        ]
        
        # Registrar en Google Sheets
        append_sheets("Capitalización", row)
        
        # Mensaje de confirmación
        await update.message.reply_text(
            f"✅ *Capitalización registrada exitosamente*\n\n"
            f"ID: `{datos['id']}`\n"
            f"Monto: S/ {datos['monto']:.2f}\n\n"
            f"Ahora puedes usar `/evidencia {datos['id']}` para subir "
            f"un comprobante de esta operación.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="Markdown"
        )
        
        # Limpiar datos
        del datos_capitalizacion[user_id]
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error al registrar capitalización: {e}")
        
        await update.message.reply_text(
            "❌ Ha ocurrido un error al registrar la capitalización. "
            "Por favor, inténtalo de nuevo más tarde.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación en cualquier punto"""
    user_id = update.effective_user.id
    
    # Limpiar datos
    if user_id in datos_capitalizacion:
        del datos_capitalizacion[user_id]
    
    await update.message.reply_text(
        "Operación cancelada. No se ha registrado ninguna capitalización.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def register_capitalizacion_handlers(application):
    """Registra los handlers para el módulo de capitalización"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("capitalizacion", capitalizacion_command)],
        states={
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_step)],
            ORIGEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, origen_step)],
            DESTINO: [MessageHandler(filters.TEXT & ~filters.COMMAND, destino_step)],
            CONCEPTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, concepto_step)],
            NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, notas_step)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handler de capitalización registrado")
