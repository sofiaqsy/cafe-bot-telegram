import logging
from telegram.ext import Application, CommandHandler

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Importar configuración
from config import TOKEN

# Importar handlers
from handlers.start import start_command, help_command
from handlers.compras import register_compras_handlers
from handlers.proceso import register_proceso_handlers
from handlers.gastos import register_gastos_handlers
from handlers.ventas import register_ventas_handlers
from handlers.reportes import register_reportes_handlers

def main():
    """Iniciar el bot"""
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
    
    # Iniciar el bot
    logger.info("Bot iniciado")
    application.run_polling()

if __name__ == "__main__":
    main()