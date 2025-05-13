import os
import logging
from telegram.ext import Application, CommandHandler
from telegram.ext import ExtBot
from telegram.ext.filters import UpdateType
import asyncio
from tornado.httpclient import AsyncHTTPClient
from tornado.web import Application as WebApplication, RequestHandler
from tornado.ioloop import IOLoop
import json

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

# Clase para manejar webhooks
class WebhookHandler(RequestHandler):
    def initialize(self, application):
        self.application = application

    async def post(self):
        try:
            # Obtener el cuerpo de la solicitud
            body = json.loads(self.request.body)
            # Procesar la actualización de Telegram
            await self.application.process_update(body)
            # Responder con éxito
            self.set_status(200)
        except Exception as e:
            logger.error(f"Error al procesar la actualización: {e}")
            self.set_status(500)

# Función para eliminar el webhook antes de iniciar el bot (por seguridad)
async def delete_webhook():
    try:
        # Construir la URL para eliminar el webhook
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        # Hacer la solicitud HTTP
        client = AsyncHTTPClient()
        response = await client.fetch(url, method="POST")
        logger.info(f"Webhook eliminado: {response.body}")
    except Exception as e:
        logger.error(f"Error al eliminar webhook: {e}")

# Función para configurar el webhook
async def set_webhook(app_url):
    try:
        # Construir la URL para configurar el webhook
        webhook_url = f"{app_url}/webhook/{TOKEN}"
        url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        # Hacer la solicitud HTTP
        client = AsyncHTTPClient()
        response = await client.fetch(url, method="POST")
        logger.info(f"Webhook configurado en {webhook_url}: {response.body}")
    except Exception as e:
        logger.error(f"Error al configurar webhook: {e}")

def main():
    """Iniciar el bot para Heroku"""
    logger.info("Iniciando bot de Telegram para Gestión de Café en Heroku")
    
    # Obtener la URL de la aplicación Heroku
    app_url = os.environ.get("APP_URL")
    if not app_url:
        logger.error("Variable de entorno APP_URL no configurada. No se puede configurar el webhook.")
        return
    
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
        "GOOGLE_CREDENTIALS",
        "APP_URL",
        "PORT"
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var in ["GOOGLE_CREDENTIALS", "TELEGRAM_BOT_TOKEN"]:
                logger.info(f"Variable de entorno {var} está configurada (valor no mostrado por seguridad)")
            else:
                logger.info(f"Variable de entorno {var} está configurada: {value}")
        else:
            logger.warning(f"Variable de entorno {var} NO está configurada")
    
    # Crear la aplicación de Telegram
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
    
    # Configurar la aplicación web para manejar webhooks
    port = int(os.environ.get('PORT', 8443))
    web_app = WebApplication([
        (f"/webhook/{TOKEN}", WebhookHandler, dict(application=application))
    ])
    
    # Eliminar y configurar el webhook
    loop = asyncio.get_event_loop()
    loop.run_until_complete(delete_webhook())
    loop.run_until_complete(set_webhook(app_url))
    
    # Iniciar la aplicación web
    logger.info(f"Iniciar servidor web en puerto {port}")
    web_app.listen(port)
    
    # Iniciar el loop de eventos
    logger.info("Bot iniciado con webhook configurado. Esperando comandos...")
    IOLoop.current().start()

if __name__ == "__main__":
    main()