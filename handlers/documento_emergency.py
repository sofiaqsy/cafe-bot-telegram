import logging
import os
import uuid
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes

# Configuración básica de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Comando de emergencia para documento
async def documento_emergency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando de emergencia alternativo para cuando /documento no funciona
    """
    user = update.effective_user
    logger.info(f"Comando /evidencia usado por {user.username or user.first_name} (ID: {user.id})")
    
    # Responder al usuario con instrucciones alternativas
    await update.message.reply_text(
        "🚨 *SISTEMA ALTERNATIVO DE EVIDENCIAS* 🚨\n\n"
        "El comando /documento está temporalmente en mantenimiento.\n\n"
        "Para registrar evidencia de pago, sigue estos pasos simples:\n\n"
        "1️⃣ Envía una *foto* de la evidencia directamente en este chat\n"
        "2️⃣ En el *texto* de la foto incluye:\n"
        "   • Tipo: COMPRA o VENTA\n"
        "   • ID: El código de la operación\n"
        "   • Descripción: Cualquier detalle relevante\n\n"
        "Ejemplo: \"*Tipo: COMPRA, ID: C-2025-0042, Pago a proveedor Juan Pérez*\"\n\n"
        "Un administrador procesará tu evidencia manualmente.\n"
        "Recibirás confirmación dentro de las próximas 24 horas.",
        parse_mode="Markdown"
    )
    
    # Mostrar ejemplos de formato
    keyboard = [["📷 Ver ejemplo de formato"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Puedes ver un ejemplo del formato correcto:",
        reply_markup=reply_markup
    )
    
    return

# Función para registrar el handler del comando de emergencia
def register_documento_emergency(application):
    """
    Registra el handler de emergencia en la aplicación
    """
    from telegram.ext import CommandHandler, MessageHandler, filters
    
    # Registrar el comando principal alternativo
    application.add_handler(CommandHandler("evidencia", documento_emergency))
    
    # También registrar con el nombre original para maximizar compatibilidad
    application.add_handler(CommandHandler("documento", documento_emergency))
    
    # Manejar click en botón de ejemplo
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^📷 Ver ejemplo de formato$"), 
            ejemplo_formato
        )
    )
    
    logger.info("Handler de emergencia para documentos registrado correctamente")
    return True

# Función para mostrar ejemplo de formato
async def ejemplo_formato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra un ejemplo del formato correcto para enviar evidencias"""
    # Responder con mensaje explicativo
    await update.message.reply_text(
        "Este es un ejemplo de cómo enviar correctamente una evidencia:\n\n"
        "1. Toma una foto clara del comprobante de pago\n"
        "2. Envía la imagen con un texto como este:\n\n"
        "Tipo: COMPRA\n"
        "ID: C-2025-0042\n"
        "Descripción: Pago a proveedor Juan Pérez, 50kg café",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Enviar una imagen de ejemplo si está disponible
    try:
        await update.message.reply_photo(
            photo="https://i.imgur.com/tJVmwOV.png",  # Imagen genérica de ejemplo
            caption="👆 Asegúrate de que la imagen sea clara y legible"
        )
    except Exception as e:
        logger.error(f"Error al enviar imagen de ejemplo: {e}")
        # Continuar incluso si la imagen falla
    
    await update.message.reply_text(
        "Usa /evidencia si necesitas ver estas instrucciones de nuevo.\n\n"
        "Gracias por tu comprensión mientras solucionamos el sistema principal."
    )
    
    return