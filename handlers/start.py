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
        "*/compra_adelanto* - Compra con adelanto\n"
        "*/gasto* - Registrar gastos\n"
        "*/adelanto* - Registrar adelanto a proveedor\n"
        "*/proceso* - Registrar procesamiento de café\n"
        "*/venta* - Registrar una venta\n"
        "*/capitalizacion* - Registrar ingreso de capital\n"
        "*/reporte* - Ver reportes y estadísticas\n"
        "*/pedido* - Registrar pedido de cliente\n"
        "*/pedidos* - Ver pedidos pendientes\n"
        "*/adelantos* - Ver adelantos vigentes\n"
        "*/almacen* - Gestionar almacén central\n"
        "*/evidencia* - Cargar evidencia de pago de compras/ventas\n"
        "*/ayuda* - Ver esta ayuda\n\n"
        "Para más información, consulta la documentación completa.",
        parse_mode="Markdown"
    )