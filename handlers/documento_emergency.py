import os
import logging
import datetime
import uuid
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Definir directorio de uploads
UPLOADS_FOLDER = os.environ.get("UPLOADS_FOLDER", "uploads")
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# Comprobar si tenemos permisos de escritura en el directorio de uploads
try:
    test_file_path = os.path.join(UPLOADS_FOLDER, "test_write.tmp")
    with open(test_file_path, 'w') as f:
        f.write("test")
    os.remove(test_file_path)
    logger.info(f"Permisos de escritura verificados en: {UPLOADS_FOLDER}")
except Exception as e:
    logger.error(f"Error al verificar permisos de escritura: {e}")

# Handler de emergencia para documentos
async def documento_emergencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de emergencia simplificado para el comando /documento"""
    try:
        user = update.effective_user
        logger.info(f"Comando /documento ejecutado por {user.username or user.first_name} (ID: {user.id})")
        
        # Mostrar instrucciones para enviar la evidencia
        keyboard = [["COMPRA"], ["VENTA"], ["❌ Cancelar"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "📝 *REGISTRO DE EVIDENCIA DE PAGO*\n\n"
            "Este es un sistema temporal para registrar evidencias de pago.\n\n"
            "Por favor, sigue estos pasos:\n"
            "1. Selecciona el tipo de operación (COMPRA o VENTA)\n"
            "2. Cuando te lo indique, envía el ID de la operación\n"
            "3. Luego, envía la imagen de la evidencia\n\n"
            "Selecciona el tipo de operación:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Guardar estado en user_data para seguir la conversación
        context.user_data["documento_emergency"] = {
            "state": "waiting_type",
            "user_id": user.id,
            "username": user.username or user.first_name
        }
        
        # Registrar en next_step_handler
        context.application.create_task(
            handle_documento_conversation(update, context)
        )
        
    except Exception as e:
        logger.error(f"Error en documento_emergencia: {e}")
        await update.message.reply_text(
            "❌ Ha ocurrido un error al iniciar el proceso. Por favor, intenta nuevamente o contacta al administrador.",
            reply_markup=ReplyKeyboardRemove()
        )

async def handle_documento_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja la conversación de documento fuera del ConversationHandler"""
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Esperar tipo de operación
        message = await context.bot.send_message(
            chat_id=chat_id,
            text="Estoy esperando tu selección...",
            reply_markup=ReplyKeyboardMarkup([["COMPRA"], ["VENTA"], ["❌ Cancelar"]], one_time_keyboard=True, resize_keyboard=True)
        )
        
        # Esperar respuesta del usuario manualmente
        # Nota: Este es un enfoque simplificado y no es ideal, pero funciona para una solución de emergencia
        # En el futuro, implementar correctamente usando ConversationHandler
        
        # Para completar la conversación manualmente, podemos usar un CommandHandler para /finalizar_documento
        # que procese los datos almacenados en context.user_data["documento_emergency"]
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ SISTEMA TEMPORAL DE EVIDENCIAS ⚠️\n\n"
                 "Debido a una actualización en el sistema, por favor envía tu evidencia como una foto normal en el chat, "
                 "incluyendo en el texto de la imagen:\n\n"
                 "- Tipo: COMPRA o VENTA\n"
                 "- ID de la operación\n\n"
                 "Un administrador procesará tu evidencia manualmente lo antes posible.",
            reply_markup=ReplyKeyboardRemove()
        )
        
    except Exception as e:
        logger.error(f"Error en handle_documento_conversation: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Ha ocurrido un error en el proceso. Por favor, envía tu evidencia directamente como foto con descripción.",
            reply_markup=ReplyKeyboardRemove()
        )

# Handler para fotos que podrían ser evidencias
async def procesar_foto_evidencia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa fotos enviadas que podrían ser evidencias de pago"""
    try:
        user = update.effective_user
        caption = update.message.caption or ""
        logger.info(f"Foto recibida de {user.username or user.first_name} (ID: {user.id}) con caption: {caption[:50]}...")
        
        # Verificar si parece una evidencia de pago
        is_evidencia = False
        tipo = None
        operacion_id = None
        
        # Buscar palabras clave en el caption
        caption_lower = caption.lower()
        if any(word in caption_lower for word in ["compra", "venta", "pago", "evidencia", "documento"]):
            is_evidencia = True
            
            # Intentar extraer tipo
            if "compra" in caption_lower:
                tipo = "COMPRA"
            elif "venta" in caption_lower:
                tipo = "VENTA"
            
            # Buscar posible ID (formatos comunes como A-2023-001, C-2025-0042, etc.)
            import re
            id_matches = re.findall(r'[A-Z]-\d{4}-\d+', caption)
            if id_matches:
                operacion_id = id_matches[0]
        
        # Si parece una evidencia, guardar la foto y registrar
        if is_evidencia:
            # Obtener la foto de mejor calidad
            photo = update.message.photo[-1]
            file_id = photo.file_id
            
            # Descargar la foto
            file = await context.bot.get_file(file_id)
            
            # Generar nombre de archivo único
            ahora = datetime.datetime.now()
            filename = f"evidencia_{user.id}_{ahora.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(UPLOADS_FOLDER, filename)
            
            # Guardar la foto
            await file.download_to_drive(filepath)
            
            # Registrar en el log
            logger.info(f"Evidencia guardada: {filepath}")
            logger.info(f"Detalles: Tipo={tipo}, ID={operacion_id}, Usuario={user.username or user.first_name}")
            
            # Confirmar al usuario
            await update.message.reply_text(
                f"✅ *Evidencia registrada correctamente*\n\n"
                f"Archivo: {filename}\n"
                f"Tipo: {tipo or 'No especificado'}\n"
                f"ID operación: {operacion_id or 'No especificado'}\n\n"
                f"Un administrador procesará tu evidencia pronto.",
                parse_mode="Markdown"
            )
        
    except Exception as e:
        logger.error(f"Error en procesar_foto_evidencia: {e}")
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar la imagen. Si estabas enviando una evidencia de pago, "
            "por favor menciona claramente en el texto 'EVIDENCIA DE PAGO' junto con el tipo (COMPRA/VENTA) "
            "y el ID de la operación."
        )

# Función para registrar los handlers
def register_documento_emergency_handlers(application):
    """Registra los handlers de emergencia para documentos"""
    from telegram.ext import CommandHandler, MessageHandler, filters
    
    try:
        # Registrar handler principal
        application.add_handler(CommandHandler("documento", documento_emergencia))
        logger.info("Handler de emergencia para /documento registrado correctamente")
        
        # Registrar handler para procesar fotos
        application.add_handler(MessageHandler(filters.PHOTO, procesar_foto_evidencia))
        logger.info("Handler para procesar fotos registrado correctamente")
        
        # Registrar comando de estado
        async def documento_status(update, context):
            await update.message.reply_text(
                "🔧 *Sistema de documentos: MODO DE EMERGENCIA*\n\n"
                "El sistema de documentos está operando en modo de emergencia.\n\n"
                "Para registrar una evidencia de pago:\n"
                "1. Usa el comando /documento, o\n"
                "2. Envía directamente la foto con una descripción que incluya:\n"
                "   - La palabra 'compra' o 'venta'\n"
                "   - El ID de la operación\n\n"
                "La evidencia será procesada manualmente por un administrador.",
                parse_mode="Markdown"
            )
        
        application.add_handler(CommandHandler("documento_status", documento_status))
        logger.info("Handler para /documento_status registrado correctamente")
        
        return True
    except Exception as e:
        logger.error(f"Error al registrar handlers de emergencia para documentos: {e}")
        return False