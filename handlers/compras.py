import logging
import datetime
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from config import COMPRAS_FILE
from utils.db import append_data

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
PROVEEDOR, CANTIDAD, PRECIO, CALIDAD, CONFIRMAR = range(5)

# Datos temporales
datos_compra = {}

# Headers para la hoja de compras
COMPRAS_HEADERS = ["fecha", "proveedor", "cantidad", "precio", "calidad", "total"]

async def compra_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de compra"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /compra")
    await update.message.reply_text(
        "Vamos a registrar una nueva compra de café.\n\n"
        "Por favor, ingresa el nombre del proveedor:"
    )
    return PROVEEDOR

async def proveedor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el proveedor y solicita la cantidad"""
    user_id = update.effective_user.id
    proveedor_nombre = update.message.text
    logger.info(f"Usuario {user_id} ingresó proveedor: {proveedor_nombre}")
    
    datos_compra[user_id] = {"proveedor": proveedor_nombre}
    
    await update.message.reply_text(
        f"Proveedor: {proveedor_nombre}\n\n"
        "Ahora, ingresa la cantidad de café en kg:"
    )
    return CANTIDAD

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita el precio"""
    user_id = update.effective_user.id
    try:
        cantidad = float(update.message.text)
        logger.info(f"Usuario {user_id} ingresó cantidad: {cantidad}")
        
        datos_compra[user_id]["cantidad"] = cantidad
        
        await update.message.reply_text(
            f"Cantidad: {cantidad} kg\n\n"
            "Ahora, ingresa el precio por kg (solo el número):"
        )
        return PRECIO
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para cantidad: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para la cantidad."
        )
        return CANTIDAD

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el precio y solicita la calidad"""
    user_id = update.effective_user.id
    try:
        precio = float(update.message.text)
        logger.info(f"Usuario {user_id} ingresó precio: {precio}")
        
        datos_compra[user_id]["precio"] = precio
        
        await update.message.reply_text(
            f"Precio: {precio} por kg\n\n"
            "Por último, califica la calidad del café (1-5 estrellas):"
        )
        return CALIDAD
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para precio: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el precio."
        )
        return PRECIO

async def calidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la calidad y solicita confirmación"""
    user_id = update.effective_user.id
    try:
        calidad = int(update.message.text)
        logger.info(f"Usuario {user_id} ingresó calidad: {calidad}")
        
        if 1 <= calidad <= 5:
            datos_compra[user_id]["calidad"] = calidad
            
            # Mostrar resumen para confirmar
            compra = datos_compra[user_id]
            total = compra["cantidad"] * compra["precio"]
            
            # Guardar el total en los datos
            datos_compra[user_id]["total"] = total
            
            await update.message.reply_text(
                "📝 *Resumen de la compra*\n\n"
                f"Proveedor: {compra['proveedor']}\n"
                f"Cantidad: {compra['cantidad']} kg\n"
                f"Precio: {compra['precio']} por kg\n"
                f"Calidad: {'⭐' * compra['calidad']}\n"
                f"Total: {total}\n\n"
                "¿Confirmar esta compra? (Sí/No)",
                parse_mode="Markdown"
            )
            return CONFIRMAR
        else:
            logger.warning(f"Usuario {user_id} ingresó un valor fuera de rango para calidad: {calidad}")
            await update.message.reply_text(
                "Por favor, ingresa un número del 1 al 5 para la calidad."
            )
            return CALIDAD
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para calidad: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para la calidad."
        )
        return CALIDAD

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda la compra"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    logger.info(f"Usuario {user_id} respondió a confirmación: {respuesta}")
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Preparar datos para guardar
        compra = datos_compra[user_id].copy()
        
        # Añadir fecha
        compra["fecha"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Guardando compra en Google Sheets: {compra}")
        
        # Guardar la compra en Google Sheets a través de db.py
        try:
            # Llamar a la función para guardar los datos (ahora sin pasar el parámetro headers)
            append_data(COMPRAS_FILE, compra, COMPRAS_HEADERS)
            
            logger.info(f"Compra guardada exitosamente para usuario {user_id}")
            
            await update.message.reply_text(
                "✅ ¡Compra registrada exitosamente!\n\n"
                "Usa /compra para registrar otra compra."
            )
        except Exception as e:
            logger.error(f"Error al guardar compra: {e}")
            await update.message.reply_text(
                "❌ Error al guardar la compra. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}\n\n"
                "Contacta al administrador si el problema persiste."
            )
    else:
        logger.info(f"Usuario {user_id} canceló la compra")
        await update.message.reply_text(
            "❌ Compra cancelada.\n\n"
            "Usa /compra para iniciar de nuevo."
        )
    
    # Limpiar datos temporales
    if user_id in datos_compra:
        del datos_compra[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló el proceso de compra con /cancelar")
    
    # Limpiar datos temporales
    if user_id in datos_compra:
        del datos_compra[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /compra para iniciar de nuevo cuando quieras."
    )
    
    return ConversationHandler.END

def register_compras_handlers(application):
    """Registra los handlers para el módulo de compras"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compra", compra_command)],
        states={
            PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
            CALIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, calidad)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handlers de compras registrados")