"""
Manejador para el comando /evidencia.
Este comando es un alias simplificado del comando /documento,
específicamente para que sea más intuitivo para los usuarios.
"""

import logging
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
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"Usuario {username} (ID: {user_id}) ejecutó el comando /evidencia")
    
    # Simplemente redirigimos al comando /documento para mantener un solo flujo
    return await documento_command(update, context)

def register_evidencias_handlers(application):
    """Registra los handlers para el módulo de evidencias"""
    # Agregar el comando /evidencia como alias de /documento
    application.add_handler(CommandHandler("evidencia", evidencia_command))
    logger.info("Handler de evidencias registrado")
