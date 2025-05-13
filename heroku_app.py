import os
import logging
import requests
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Asegurarse de que los logs de las bibliotecas no sean demasiado verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Cargar variables de entorno directamente
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Importar el resto de módulos después de cargar las variables de entorno
from utils.sheets import initialize_sheets

# Importar handlers
from handlers.start import start_command, help_command
from handlers.compras import register_compras_handlers
from handlers.proceso import register_proceso_handlers
from handlers.gastos import register_gastos_handlers
from handlers.ventas import register_ventas_handlers
from handlers.reportes import register_reportes_handlers
from handlers.pedidos import register_pedidos_handlers
from handlers.adelantos import register_adelantos_handlers
from handlers.compra_adelanto import register_compra_adelanto_handlers

def eliminar_webhook():
    """Elimina cualquier webhook configurado antes de iniciar el polling"""
    try:
        logger.info("Eliminando webhook existente...")
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        logger.info(f"Realizando solicitud a: {url.replace(TOKEN, TOKEN[:5] + '...')}")
        
        response = requests.get(url)
        logger.info(f"Respuesta del servidor: Código {response.status_code}")
        
        if response.status_code == 200 and response.json().get("ok"):
            logger.info("Webhook eliminado correctamente")
            return True
        else:
            logger.error(f"Error al eliminar webhook: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al eliminar webhook: {e}")
        return False

def main():
    """Iniciar el bot con polling para Heroku"""
    logger.info("Iniciando bot de Telegram para Gestión de Café en Heroku")
    
    # Verificar el token (seguro, solo muestra los primeros 5 caracteres)
    if not TOKEN:
        logger.error("¡ERROR! No se encontró el token de Telegram en las variables de entorno")
        return
    else:
        logger.info(f"Token encontrado (primeros 5 caracteres): {TOKEN[:5]}...")
    
    # Eliminar webhook existente
    if not eliminar_webhook():
        logger.warning("No se pudo eliminar el webhook. Intentando continuar de todos modos...")
    
    # Inicializar Google Sheets
    try:
        logger.info("Inicializando Google Sheets...")
        initialize_sheets()
        logger.info("Google Sheets inicializado correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar Google Sheets: {e}")
        logger.warning("El bot continuará funcionando, pero los datos no se guardarán en Google Sheets")
    
    # Crear la aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Registrar comandos básicos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Registrar handlers específicos
    register_compras_handlers(application)
    register_proceso_handlers(application)
    register_gastos_handlers(application)
    register_ventas_handlers(application)
    register_reportes_handlers(application)
    register_pedidos_handlers(application)
    register_adelantos_handlers(application)
    register_compra_adelanto_handlers(application)
    
    # IMPORTANTE: Usar POLLING, no webhook
    logger.info("Bot iniciado en modo POLLING. Esperando comandos...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()