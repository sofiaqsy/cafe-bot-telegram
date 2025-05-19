import logging
import os
import platform
import sys
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

# Configurar logging
logger = logging.getLogger(__name__)

async def diagnostico_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Comando para diagnosticar el estado del bot"""
    user_id = update.effective_user.id
    logger.info(f"Comando /diagnostico solicitado por usuario {user_id}")
    
    # Recopilar información del sistema
    info_sistema = {
        "Sistema Operativo": platform.system(),
        "Versión": platform.version(),
        "Arquitectura": platform.machine(),
        "Python": sys.version.split()[0],
        "Pid": os.getpid()
    }
    
    # Recopilar información del entorno
    variables_entorno = {
        "DRIVE_ENABLED": os.getenv("DRIVE_ENABLED", "No configurado"),
        "UPLOADS_FOLDER": os.getenv("UPLOADS_FOLDER", "No configurado"),
        "SPREADSHEET_ID": "Configurado" if os.getenv("SPREADSHEET_ID") else "No configurado",
        "GOOGLE_CREDENTIALS": "Configurado" if os.getenv("GOOGLE_CREDENTIALS") else "No configurado"
    }
    
    # Verificar directorios
    directorio_uploads = "uploads"
    existe_directorio = os.path.exists(directorio_uploads)
    es_escribible = os.access(directorio_uploads, os.W_OK) if existe_directorio else False
    
    # Componer mensaje de respuesta
    mensaje = (
        "🔍 *DIAGNÓSTICO DEL BOT* 🔍\n\n"
        "*Información del Sistema:*\n"
    )
    
    for clave, valor in info_sistema.items():
        mensaje += f"- {clave}: {valor}\n"
    
    mensaje += "\n*Variables de Entorno:*\n"
    for clave, valor in variables_entorno.items():
        mensaje += f"- {clave}: {valor}\n"
    
    mensaje += f"\n*Directorio de Uploads:*\n"
    mensaje += f"- Existe: {'Sí' if existe_directorio else 'No'}\n"
    mensaje += f"- Escribible: {'Sí' if es_escribible else 'No'}\n"
    
    mensaje += "\n*Comandos Disponibles:*\n"
    mensaje += "- /documento - Cargar evidencia de pago\n"
    mensaje += "- /documento_test - Probar disponibilidad del handler\n"
    mensaje += "- /diagnostico - Ver este diagnóstico\n"
    
    mensaje += "\n*Instrucciones de Depuración:*\n"
    mensaje += "1. Intenta el comando /documento_test primero\n"
    mensaje += "2. Si responde, el handler está registrado\n"
    mensaje += "3. Si no, revisa los logs del servidor\n"
    mensaje += "4. Verifica que la carpeta 'uploads' tenga permisos correctos\n"
    
    await update.message.reply_text(
        mensaje,
        parse_mode="Markdown"
    )
    
    logger.info(f"Diagnóstico enviado al usuario {user_id}")

def register_diagnostico_handlers(application):
    """Registra los handlers para el módulo de diagnóstico"""
    try:
        logger.info("Registrando handler de diagnóstico...")
        application.add_handler(CommandHandler("diagnostico", diagnostico_command))
        logger.info("Handler de diagnóstico registrado correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al registrar handler de diagnóstico: {e}")
        return False