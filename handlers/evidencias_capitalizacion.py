import logging
import os
import uuid
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler
from utils.sheets import get_filtered_data
from config import DRIVE_EVIDENCIAS_CAPITALIZACION_ID

# Configurar logging
logger = logging.getLogger(__name__)

# Asegurar que existe el directorio de uploads para capitalización
UPLOADS_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
CAPITALIZACION_FOLDER = os.path.join(UPLOADS_FOLDER, "capitalizacion")

if not os.path.exists(CAPITALIZACION_FOLDER):
    os.makedirs(CAPITALIZACION_FOLDER)
    logger.info(f"Directorio para evidencias de capitalización creado: {CAPITALIZACION_FOLDER}")

async def evidencia_command_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Manejador para comandos de evidencia con ID (ej: /evidencia CAP-12345)
    Preprocesa el comando y lo redirige al manejador de evidencias principal
    """
    # Extraer el ID del comando
    mensaje = update.message.text.strip()
    partes = mensaje.split()
    
    if len(partes) < 2:
        # Si no se proporcionó un ID, mostrar un mensaje de ayuda
        await update.message.reply_text(
            "Para subir una evidencia, debes especificar el ID de la operación.\n\n"
            "Ejemplo: `/evidencia CAP-123456`\n\n"
            "Alternativamente, puedes usar el comando `/evidencia` para seleccionar "
            "el tipo de operación y ver las operaciones disponibles.",
            parse_mode="Markdown"
        )
        return
    
    # Obtener el ID
    operacion_id = partes[1]
    
    # Verificar si es un ID de capitalización
    if operacion_id.startswith("CAP-"):
        logger.info(f"Procesando comando de evidencia para capitalización ID: {operacion_id}")
        
        # Verificar si existe esta capitalización
        capitalizaciones = get_filtered_data("capitalizacion", {"id": operacion_id})
        
        if capitalizaciones and len(capitalizaciones) > 0:
            capitalizacion = capitalizaciones[0]
            monto = capitalizacion.get("monto", "0")
            origen = capitalizacion.get("origen", "No especificado")
            destino = capitalizacion.get("destino", "No especificado")
            
            # Mostrar información de la capitalización
            mensaje = (
                f"📝 *CAPITALIZACIÓN ENCONTRADA*\n\n"
                f"ID: `{operacion_id}`\n"
                f"Monto: S/ {monto}\n"
                f"Origen: {origen}\n"
                f"Destino: {destino}\n\n"
            )
            
            # Crear un botón para iniciar el proceso de subida de evidencia
            keyboard = [
                [InlineKeyboardButton("📸 Subir evidencia", callback_data=f"evidencia_capitaliza_{operacion_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                mensaje + "Para subir una evidencia de esta capitalización, usa el botón a continuación:",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            
            # Redireccionar al flujo de evidencias
            # (aquí iría el código para iniciar el flujo, o se puede hacer desde el callback)
            
        else:
            await update.message.reply_text(
                f"⚠️ No se encontró ninguna capitalización con ID: {operacion_id}\n\n"
                "Verifica que el ID sea correcto e intenta nuevamente.",
                parse_mode="Markdown"
            )
    else:
        # Si no es un ID de capitalización, permitir que continúe al handler principal
        context.args = partes[1:]  # Pasar los argumentos al siguiente handler
        return

async def handle_evidencia_capitaliza_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el callback cuando el usuario presiona el botón para subir evidencia de capitalización
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("evidencia_capitaliza_"):
        capitalizacion_id = data.replace("evidencia_capitaliza_", "")
        
        # Informar al usuario sobre el siguiente paso
        await query.message.reply_text(
            f"Vamos a registrar una evidencia para la capitalización {capitalizacion_id}.\n\n"
            "Por favor, usa el comando /evidencia y selecciona 'Capitalización' "
            "en el menú de tipos de operación.",
            parse_mode="Markdown"
        )
        
        # Aquí se podría iniciar automáticamente el flujo de evidencias
        # pero para mantener la coherencia con el resto del sistema, se pide al usuario
        # que use el comando /evidencia

def register_evidencias_capitalizacion_handlers(application):
    """Registra los handlers específicos para evidencias de capitalización"""
    try:
        # Añadir handler para /evidencia con un ID de capitalización
        application.add_handler(CommandHandler("evidencia", evidencia_command_wrapper, filters=~ConversationHandler.handlers))
        
        # Añadir handler para el callback del botón
        application.add_handler(CommandHandler("callback_query", handle_evidencia_capitaliza_callback, filters=lambda query: query.data.startswith("evidencia_capitaliza_")))
        
        logger.info("Handlers de evidencias para capitalización registrados")
        return True
    except Exception as e:
        logger.error(f"Error al registrar handlers de evidencias para capitalización: {e}")
        return False