"""
Single entry point that runs both the Telegram bot and the Flask web app
in the same process — one dyno instead of two.

- Flask runs in a background thread on the PORT provided by Heroku.
- The Telegram bot runs in the main thread using run_polling().
"""
import logging
import os
import threading
import traceback

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

from config import TOKEN
from handlers.start import start_command, help_command
from handlers.compras import register_compras_handlers
from handlers.gastos import register_gastos_handlers
from handlers.adelantos import register_adelantos_handlers
from handlers.capitalizacion import register_capitalizacion_handlers
from handlers.compra_mixta import register_compra_mixta_handlers
from handlers.asistente import register_asistente_handlers
from web import app as flask_app


def start_web():
    """Run Flask in a background thread."""
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"=== INICIANDO WEB en puerto {port} ===")
    flask_app.run(host="0.0.0.0", port=port, use_reloader=False)


def eliminar_webhook():
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        response = requests.get(url)
        if response.status_code == 200 and response.json().get("ok"):
            logger.info("Webhook eliminado correctamente")
        else:
            logger.error(f"Error al eliminar webhook: {response.text}")
    except Exception as e:
        logger.error(f"Excepción al eliminar webhook: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"[ERROR HANDLER] Excepción no manejada: {context.error}")
    logger.error(traceback.format_exc())
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("❌ Ocurrió un error inesperado. Intenta de nuevo.")


def main():
    # Start Flask web in background thread
    web_thread = threading.Thread(target=start_web, daemon=True)
    web_thread.start()

    # Start Telegram bot in main thread
    logger.info("=== INICIANDO BOT DE CAFE ===")
    eliminar_webhook()

    try:
        application = Application.builder().token(TOKEN).build()
    except Exception as e:
        logger.error(f"ERROR CRÍTICO al crear aplicación: {e}")
        logger.error(traceback.format_exc())
        return

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CommandHandler("help", help_command))

    register_compras_handlers(application)
    register_gastos_handlers(application)
    register_adelantos_handlers(application)
    register_capitalizacion_handlers(application)
    register_compra_mixta_handlers(application)
    register_asistente_handlers(application)
    application.add_error_handler(error_handler)

    logger.info("Todos los handlers registrados. Bot iniciando en modo POLLING...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        logger.error(traceback.format_exc())
