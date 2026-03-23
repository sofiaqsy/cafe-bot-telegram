from telegram import Update
from telegram.ext import ContextTypes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for the /start command."""
    user = update.effective_user
    await update.message.reply_text(
        f"¡Hola {user.first_name}! 👋\n\n"
        "Bienvenido al Bot de Gestión de Café ☕\n\n"
        "Usa /ayuda para ver los comandos disponibles."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /help and /ayuda commands."""
    await update.message.reply_text(
        "🤖 *Comandos disponibles*\n\n"
        "☕ *COMPRAS*\n"
        "*/compra* - Registrar una nueva compra de café\n"
        "*/compra\\_mixta* - Compra con pagos combinados (efectivo + adelanto)\n\n"
        "💰 *FINANZAS*\n"
        "*/gasto* - Registrar un gasto operativo\n"
        "*/adelanto* - Registrar un adelanto a proveedor\n"
        "*/adelantos* - Ver adelantos vigentes\n"
        "*/capitalizacion* - Registrar ingreso de capital\n\n"
        "*/ayuda* - Ver esta ayuda",
        parse_mode="Markdown"
    )
