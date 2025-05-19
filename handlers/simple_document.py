import logging
import traceback
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# Estados simplificados para la conversación
SELECCIONAR_TIPO, SELECCIONAR_ID, SUBIR_DOCUMENTO, CONFIRMAR = range(4)

# Tipos de operaciones soportadas
TIPOS_OPERACION = ["COMPRA", "VENTA"]

async def simple_documento_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Implementación simplificada del comando documento que siempre funcionará"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        logger.info(f"==== COMANDO /documento ALTERNATIVO INICIADO por {username} (ID: {user_id}) ====")
        
        # Crear teclado con opciones
        keyboard = [[tipo] for tipo in TIPOS_OPERACION]
        keyboard.append(["❌ Cancelar"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "📎 CARGAR DOCUMENTO DE EVIDENCIA DE PAGO\n\n"
            "Selecciona el tipo de operación al que pertenece el documento:",
            reply_markup=reply_markup
        )
        
        # Store context for the conversation
        context.user_data["simple_documento"] = {
            "registrado_por": username
        }
        
        # Return the expected state
        return SELECCIONAR_TIPO
    
    except Exception as e:
        logger.error(f"ERROR en simple_documento_command: {e}")
        logger.error(traceback.format_exc())
        
        # Notify the user about the error
        await update.message.reply_text(
            "⚠️ El sistema de documentos está en mantenimiento. Por favor, intenta más tarde o contacta al administrador.\n\n"
            "Mientras tanto, puedes enviar la evidencia de pago directamente al administrador por este medio.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

async def simple_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Versión simple de cancelar operación"""
    try:
        await update.message.reply_text(
            "❌ Operación cancelada.\n\n"
            "Usa /documento para iniciar de nuevo cuando quieras.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Clean up user data
        if "simple_documento" in context.user_data:
            del context.user_data["simple_documento"]
            
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"ERROR en simple_cancelar: {e}")
        logger.error(traceback.format_exc())
        
        await update.message.reply_text(
            "Operación cancelada.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END