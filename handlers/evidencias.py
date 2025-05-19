"""
Manejador para el comando /evidencia.
Este comando es un alias simplificado del comando /documento,
específicamente para que sea más intuitivo para los usuarios.
"""

import logging
import traceback
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes
from handlers.documents import documento_command, register_documents_handlers

# Configurar logging
logger = logging.getLogger(__name__)

async def evidencia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Alias del comando /documento para subir evidencias
    Este comando redirige al flujo de /documento para mantener la coherencia
    """
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        logger.info(f"=== COMANDO /evidencia INICIADO por {username} (ID: {user_id}) ===")
        
        # Log adicional para verificar el flujo
        logger.info("Redirigiendo al flujo de /documento para seleccionar tipo de operación")
        
        # Simplemente redirigimos al comando /documento para mantener un solo flujo
        result = await documento_command(update, context)
        
        logger.info(f"Redirección a /documento completada con resultado: {result}")
        return result
    
    except Exception as e:
        logger.error(f"ERROR en evidencia_command: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar el comando /evidencia.\n"
            "Por favor, intenta usar el comando /documento como alternativa."
        )
        
        return -1  # Terminar la conversación

def register_evidencias_handlers(application):
    """Registra los handlers para el módulo de evidencias"""
    try:
        # Agregar el comando /evidencia como alias de /documento
        logger.info("Registrando handler para el comando /evidencia...")
        application.add_handler(CommandHandler("evidencia", evidencia_command))
        logger.info("Handler de evidencias registrado correctamente")
        return True
    except Exception as e:
        logger.error(f"ERROR al registrar handler de evidencias: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
