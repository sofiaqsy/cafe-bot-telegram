import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from datetime import datetime
import traceback

# Importar módulos para Google Sheets
from utils.db import append_data

# Estados para la conversación
PROVEEDOR, MONTO, NOTAS, CONFIRMAR = range(4)

# Logger
logger = logging.getLogger(__name__)

# Headers para la hoja de adelantos
ADELANTOS_HEADERS = ["fecha", "hora", "proveedor", "monto", "saldo_restante", "notas", "registrado_por"]

# Función para obtener fecha y hora actuales
def get_now():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

# Funciones para el manejo de adelantos
async def adelanto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar el proceso de registro de adelanto"""
    await update.message.reply_text(
        "📝 Registro de adelanto a proveedor\n\n"
        "Los adelantos son pagos anticipados a proveedores que se descontarán de futuras compras.\n\n"
        "Por favor, ingresa el nombre del proveedor:"
    )
    return PROVEEDOR

async def proveedor_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir nombre del proveedor"""
    context.user_data['proveedor'] = update.message.text.strip()
    
    # Verificar si ya tiene adelantos vigentes
    # (Esta funcionalidad completa se implementará cuando se integre Google Sheets)
    
    await update.message.reply_text(
        "💸 ¿Cuál es el monto del adelanto? (en S/)"
    )
    return MONTO

async def monto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir monto del adelanto"""
    try:
        monto_text = update.message.text.replace(',', '.').strip()
        monto = float(monto_text)
        
        if monto <= 0:
            await update.message.reply_text("⚠️ El monto debe ser mayor a cero. Intenta de nuevo:")
            return MONTO
        
        context.user_data['monto'] = monto
        context.user_data['saldo_restante'] = monto
        
        await update.message.reply_text(
            "📝 Opcionalmente, puedes agregar notas o detalles sobre este adelanto:\n"
            "(Envía '-' si no deseas agregar notas)"
        )
        return NOTAS
    except ValueError:
        await update.message.reply_text(
            "⚠️ El valor ingresado no es válido. Por favor, ingresa solo números:"
        )
        return MONTO

async def notas_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir notas adicionales"""
    if update.message.text.strip() == '-':
        context.user_data['notas'] = ''
    else:
        context.user_data['notas'] = update.message.text.strip()
    
    # Mostrar resumen para confirmar
    await update.message.reply_text(
        f"📋 RESUMEN DEL ADELANTO\n\n"
        f"Proveedor: {context.user_data['proveedor']}\n"
        f"Monto: S/ {context.user_data['monto']:.2f}\n"
        f"Saldo restante: S/ {context.user_data['saldo_restante']:.2f}\n"
        f"Notas: {context.user_data['notas'] or 'N/A'}\n\n"
        f"¿Confirmas este adelanto? (Sí/No)"
    )
    return CONFIRMAR

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y guardar el adelanto"""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si', 's', 'yes', 'y']:
        # Guardar el adelanto
        fecha, hora = get_now()
        
        data = {
            "fecha": fecha,
            "hora": hora,
            "proveedor": context.user_data['proveedor'],
            "monto": context.user_data['monto'],
            "saldo_restante": context.user_data['saldo_restante'],
            "notas": context.user_data['notas'],
            "registrado_por": update.effective_user.username or update.effective_user.first_name
        }
        
        try:
            # Guardar el adelanto usando la función append_data
            append_data("adelantos", data, ADELANTOS_HEADERS)
            
            await update.message.reply_text(
                f"✅ Adelanto registrado correctamente\n\n"
                f"Se ha registrado un adelanto de S/ {context.user_data['monto']:.2f} "
                f"para el proveedor {context.user_data['proveedor']}.\n\n"
                f"Este monto se descontará automáticamente de futuras compras a este proveedor."
            )
        except Exception as e:
            logger.error(f"Error guardando adelanto: {e}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                "❌ Error al registrar el adelanto. Por favor, intenta nuevamente."
            )
    else:
        await update.message.reply_text("❌ Registro cancelado")
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar_adelanto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar el registro de adelanto"""
    await update.message.reply_text(
        "❌ Registro de adelanto cancelado",
        reply_markup=None
    )
    context.user_data.clear()
    return ConversationHandler.END

async def lista_adelantos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar lista de adelantos vigentes"""
    try:
        # Esta funcionalidad completa se implementará cuando se integre Google Sheets
        await update.message.reply_text(
            "Esta función estará disponible próximamente. Se implementará la gestión de adelantos con Google Sheets."
        )
    except Exception as e:
        logger.error(f"Error obteniendo adelantos: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(f"Error al obtener los adelantos: {str(e)}")

def register_adelantos_handlers(application):
    """Registrar handlers para adelantos"""
    logger.info("Registrando handlers de adelantos")
    
    # Registro de adelantos
    adelanto_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("adelanto", adelanto_command)],
        states={
            PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor_step)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_step)],
            NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, notas_step)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_adelanto)],
    )
    
    # Listar adelantos
    application.add_handler(CommandHandler("adelantos", lista_adelantos_command))
    
    application.add_handler(adelanto_conv_handler)
    
    logger.info("Handlers de adelantos registrados correctamente")