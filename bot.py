import os
import logging
import requests
from telegram.ext import Application, CommandHandler

# Configuración de logging avanzada
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Asegurarse de que los logs de las bibliotecas no sean demasiado verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Importar configuración
from config import TOKEN, sheets_configured
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
    """Iniciar el bot"""
    logger.info("Iniciando bot de Telegram para Gestión de Café")
    
    # Verificar la configuración de Google Sheets
    if sheets_configured:
        logger.info("Inicializando Google Sheets...")
        try:
            initialize_sheets()
            logger.info("Google Sheets inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Google Sheets: {e}")
            logger.warning("El bot continuará funcionando, pero los datos no se guardarán en Google Sheets")
    else:
        logger.warning("Google Sheets no está configurado. Los datos no se guardarán correctamente.")
        logger.info("Asegúrate de configurar SPREADSHEET_ID y GOOGLE_CREDENTIALS en las variables de entorno")
    
    # Imprimir variables de entorno (solo para depuración, sin mostrar valores sensibles)
    env_vars = [
        "TELEGRAM_BOT_TOKEN", 
        "SPREADSHEET_ID", 
        "GOOGLE_CREDENTIALS"
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var == "GOOGLE_CREDENTIALS":
                logger.info(f"Variable de entorno {var} está configurada (valor no mostrado por seguridad)")
            elif var == "TELEGRAM_BOT_TOKEN":
                # Mostrar solo los primeros 10 caracteres del token, para verificar
                logger.info(f"Variable de entorno {var} está configurada: {value[:10]}...")
            else:
                logger.info(f"Variable de entorno {var} está configurada: {value}")
        else:
            logger.warning(f"Variable de entorno {var} NO está configurada")
    
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
    
    # Eliminar webhook existente
    if not eliminar_webhook():
        logger.warning("No se pudo eliminar el webhook. Intentando continuar de todos modos...")
    
    # Iniciar el bot
    logger.info("Bot iniciado. Esperando comandos...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()