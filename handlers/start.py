from telegram import Update
from telegram.ext import ContextTypes

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para el comando /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"¡Hola {user.first_name}! 👋\n\n"
        "Bienvenido al Bot de Gestión de Café ☕\n\n"
        "Este bot te ayudará a gestionar tu negocio de café, desde la compra "
        "de café en cereza hasta su venta final.\n\n"
        "Usa /ayuda para ver los comandos disponibles."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para el comando /help o /ayuda"""
    await update.message.reply_text(
        "🤖 *Comandos disponibles* 🤖\n\n"
        "*/compra* - Registrar una nueva compra de café\n"
        "*/proceso* - Registrar procesamiento de café\n"
        "*/gasto* - Registrar gastos\n"
        "*/venta* - Registrar una venta\n"
        "*/reporte* - Ver reportes y estadísticas\n"
        "*/ayuda* - Ver esta ayuda\n\n"
        "Para más información, consulta la documentación completa.",
        parse_mode="Markdown"
    )