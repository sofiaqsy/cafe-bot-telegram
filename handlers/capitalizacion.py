"""
Manejador para el comando /capitalizacion.
Este comando permite registrar un ingreso de capital al negocio con su respectivo origen y destino.
"""

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

# Opciones predefinidas para origen y destino
ORIGENES = [
    "Fondos personales", 
    "Préstamo bancario", 
    "Inversionista", 
    "Ganancias reinvertidas", 
    "Ahorros", 
    "Otro"
]

DESTINOS = [
    "Compra de café", 
    "Gastos operativos", 
    "Equipamiento", 
    "Expansión", 
    "Pago a proveedores", 
    "Fondo de emergencia", 
    "Otro"
]

# Headers para la hoja de capitalizaciones
CAPITALIZACION_HEADERS = ["id", "fecha", "monto", "origen", "destino", "concepto", "registrado_por", "notas"]

async def capitalizacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de capitalización"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /capitalizacion INICIADO por {username} (ID: {user_id}) ===")
    
    # Inicializar datos para este usuario
    datos_capitalizacion[user_id] = {
        "registrado_por": username
    }
    
    await update.message.reply_text(
        "💰 *REGISTRO DE CAPITALIZACIÓN*\n\n"
        "Vamos a registrar un nuevo ingreso de capital al negocio.\n\n"
        "Por favor, ingresa el monto a capitalizar (solo el número):",
        parse_mode="Markdown"
    )
    
    return MONTO

async def monto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el monto ingresado y solicita el origen"""
    user_id = update.effective_user.id
    try:
        # Convertir el texto a un número float
        monto_text = update.message.text.strip()
        monto = safe_float(monto_text)
        
        if monto <= 0:
            await update.message.reply_text("⚠️ El monto debe ser mayor que cero. Intenta nuevamente:")
            return MONTO
        
        logger.info(f"Usuario {user_id} ingresó monto: {monto}")
        datos_capitalizacion[user_id]["monto"] = monto
        
        # Crear teclado con opciones de origen
        keyboard = [[origen] for origen in ORIGENES]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Monto: S/ {monto}\n\n"
            "Selecciona el origen de los fondos:",
            reply_markup=reply_markup
        )
        return ORIGEN
    
    except ValueError as e:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para monto: {update.message.text}")
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para el monto."
        )
        return MONTO

async def origen_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el origen seleccionado y solicita el destino"""
    user_id = update.effective_user.id
    origen = update.message.text.strip()
    
    # Verificar si ingresó "Otro" y pedir especificación
    if origen.lower() == "otro":
        await update.message.reply_text(
            "Por favor, especifica el origen de los fondos:"
        )
        # Guardar un marcador para saber que estamos esperando una especificación
        datos_capitalizacion[user_id]["origen_especificando"] = True
        return ORIGEN
    
    # Si estábamos esperando una especificación, usar el texto ingresado como origen
    if datos_capitalizacion[user_id].get("origen_especificando", False):
        datos_capitalizacion[user_id].pop("origen_especificando", None)
    
    logger.info(f"Usuario {user_id} seleccionó origen: {origen}")
    datos_capitalizacion[user_id]["origen"] = origen
    
    # Crear teclado con opciones de destino
    keyboard = [[destino] for destino in DESTINOS]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Origen: {origen}\n\n"
        "Selecciona el destino o propósito de los fondos:",
        reply_markup=reply_markup
    )
    return DESTINO

async def destino_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el destino seleccionado y solicita el concepto"""
    user_id = update.effective_user.id
    destino = update.message.text.strip()
    
    # Verificar si ingresó "Otro" y pedir especificación
    if destino.lower() == "otro":
        await update.message.reply_text(
            "Por favor, especifica el destino o propósito de los fondos:"
        )
        # Guardar un marcador para saber que estamos esperando una especificación
        datos_capitalizacion[user_id]["destino_especificando"] = True
        return DESTINO
    
    # Si estábamos esperando una especificación, usar el texto ingresado como destino
    if datos_capitalizacion[user_id].get("destino_especificando", False):
        datos_capitalizacion[user_id].pop("destino_especificando", None)
    
    logger.info(f"Usuario {user_id} seleccionó destino: {destino}")
    datos_capitalizacion[user_id]["destino"] = destino
    
    await update.message.reply_text(
        f"Destino: {destino}\n\n"
        "Ingresa un concepto o descripción breve para esta capitalización:",
        reply_markup=ReplyKeyboardRemove()
    )
    return CONCEPTO

async def concepto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el concepto ingresado y solicita notas adicionales"""
    user_id = update.effective_user.id
    concepto = update.message.text.strip()
    
    if not concepto:
        await update.message.reply_text(
            "⚠️ El concepto no puede estar vacío. Por favor, ingresa una descripción breve:"
        )
        return CONCEPTO
    
    logger.info(f"Usuario {user_id} ingresó concepto: {concepto}")
    datos_capitalizacion[user_id]["concepto"] = concepto
    
    # Crear teclado simple para las notas
    keyboard = [["Sin notas adicionales"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"Concepto: {concepto}\n\n"
        "Opcionalmente, puedes añadir notas adicionales o detalles sobre esta capitalización.\n"
        "Si no deseas añadir notas, selecciona 'Sin notas adicionales':",
        reply_markup=reply_markup
    )
    return NOTAS

async def notas_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa las notas ingresadas y solicita confirmación"""
    user_id = update.effective_user.id
    notas = update.message.text.strip()
    
    # Si seleccionó "Sin notas adicionales", usar cadena vacía
    if notas.lower() == "sin notas adicionales":
        notas = ""
    
    logger.info(f"Usuario {user_id} ingresó notas: {notas or 'Sin notas'}")
    datos_capitalizacion[user_id]["notas"] = notas
    
    # Crear teclado para confirmación
    keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Obtener datos para el resumen
    capitalizacion = datos_capitalizacion[user_id]
    monto = capitalizacion["monto"]
    origen = capitalizacion["origen"]
    destino = capitalizacion["destino"]
    concepto = capitalizacion["concepto"]
    
    # Crear mensaje de resumen
    mensaje = "💰 *RESUMEN DE CAPITALIZACIÓN*\n\n"
    mensaje += f"Monto: S/ {monto}\n"
    mensaje += f"Origen: {origen}\n"
    mensaje += f"Destino: {destino}\n"
    mensaje += f"Concepto: {concepto}\n"
    
    if notas:
        mensaje += f"Notas: {notas}\n"
    
    mensaje += "\n¿Confirmar esta capitalización?"
    
    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return CONFIRMAR

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda la capitalización"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    
    if respuesta not in ["✅ confirmar", "confirmar", "sí", "si", "s", "yes", "y"]:
        await update.message.reply_text(
            "❌ Operación cancelada.\n\n"
            "La capitalización no ha sido registrada.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales
        if user_id in datos_capitalizacion:
            del datos_capitalizacion[user_id]
        
        return ConversationHandler.END
    
    # Preparar datos para guardar
    capitalizacion = datos_capitalizacion[user_id].copy()
    
    # Generar un ID único para esta capitalización
    capitalizacion["id"] = generate_unique_id()
    
    # Añadir fecha actualizada
    now = get_now_peru()
    fecha_formateada = now.strftime("%Y-%m-%d %H:%M")
    capitalizacion["fecha"] = format_date_for_sheets(fecha_formateada)
    
    logger.info(f"Guardando capitalización en Google Sheets: {capitalizacion}")
    
    try:
        # Crear objeto de datos limpio con los campos correctos
        datos_limpios = {
            "id": capitalizacion.get("id", ""),
            "fecha": capitalizacion.get("fecha", ""),
            "monto": capitalizacion.get("monto", ""),
            "origen": capitalizacion.get("origen", ""),
            "destino": capitalizacion.get("destino", ""),
            "concepto": capitalizacion.get("concepto", ""),
            "registrado_por": capitalizacion.get("registrado_por", ""),
            "notas": capitalizacion.get("notas", "")
        }
        
        # Guardar en Google Sheets
        result = append_sheets("capitalizaciones", datos_limpios)
        
        if result:
            logger.info(f"Capitalización guardada exitosamente para usuario {user_id}")
            
            # Preparar mensaje de éxito
            mensaje = "✅ ¡Capitalización registrada exitosamente!\n\n"
            mensaje += f"ID: {capitalizacion['id']}\n"
            mensaje += f"Monto: S/ {capitalizacion['monto']}\n"
            mensaje += f"Origen: {capitalizacion['origen']}\n"
            mensaje += f"Destino: {capitalizacion['destino']}\n"
            
            # Añadir información sobre evidencias
            mensaje += "\nPara adjuntar una evidencia de esta capitalización, "
            mensaje += "usa el comando /evidencia y selecciona 'Capitalizaciones'."
            
            await update.message.reply_text(
                mensaje,
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            logger.error("Error al guardar capitalización: La función append_sheets devolvió False")
            await update.message.reply_text(
                "❌ Error al guardar la capitalización en la base de datos.\n\n"
                "Contacta al administrador si el problema persiste.",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as e:
        logger.error(f"Error al guardar capitalización: {e}")
        await update.message.reply_text(
            "❌ Error al guardar la capitalización. Por favor, intenta nuevamente.\n\n"
            f"Error: {str(e)}\n\n"
            "Contacta al administrador si el problema persiste.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Limpiar datos temporales
    if user_id in datos_capitalizacion:
        del datos_capitalizacion[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló el proceso de capitalización con /cancelar")
    
    # Limpiar datos temporales
    if user_id in datos_capitalizacion:
        del datos_capitalizacion[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /capitalizacion para iniciar de nuevo cuando quieras.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def register_capitalizacion_handlers(application):
    """Registra los handlers para el módulo de capitalización"""
    try:
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
        return True
    except Exception as e:
        logger.error(f"Error al registrar handler de capitalización: {e}")
        return False