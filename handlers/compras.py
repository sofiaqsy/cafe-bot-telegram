import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, ConversationHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from config import COMPRAS_FILE
from utils.db import append_data

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
TIPO_CAFE, PROVEEDOR, CANTIDAD, PRECIO, CONFIRMAR = range(5)

# Tipos de café disponibles
TIPOS_CAFE = ["CEREZO", "MOTE", "PERGAMINO"]

# Datos temporales
datos_compra = {}

# Headers para la hoja de compras
COMPRAS_HEADERS = ["fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "total"]

async def compra_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de compra"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /compra")
    user_id = update.effective_user.id
    
    # Inicializar datos de compra para este usuario
    datos_compra[user_id] = {}
    
    # Crear botones para seleccionar el tipo de café
    keyboard = []
    for tipo in TIPOS_CAFE:
        keyboard.append([InlineKeyboardButton(tipo, callback_data=f"tipo_{tipo}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Vamos a registrar una nueva compra de café.\n\n"
        "Por favor, selecciona el tipo de café:",
        reply_markup=reply_markup
    )
    return TIPO_CAFE

async def tipo_cafe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar la selección del tipo de café"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    tipo_cafe = query.data.replace("tipo_", "")
    
    # Guardar el tipo de café seleccionado
    datos_compra[user_id]["tipo_cafe"] = tipo_cafe
    
    await query.edit_message_text(
        f"Tipo de café seleccionado: {tipo_cafe}\n\n"
        f"Por favor, ingresa el nombre del proveedor:"
    )
    return PROVEEDOR

async def proveedor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el proveedor y solicita la cantidad"""
    user_id = update.effective_user.id
    proveedor_nombre = update.message.text
    logger.info(f"Usuario {user_id} ingresó proveedor: {proveedor_nombre}")
    
    datos_compra[user_id]["proveedor"] = proveedor_nombre
    
    tipo_cafe = datos_compra[user_id]["tipo_cafe"]
    
    await update.message.reply_text(
        f"Tipo de café: {tipo_cafe}\n"
        f"Proveedor: {proveedor_nombre}\n\n"
        "Ahora, ingresa la cantidad de café en kg:"
    )
    return CANTIDAD

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita el precio"""
    user_id = update.effective_user.id
    try:
        cantidad = float(update.message.text.replace(',', '.'))
        logger.info(f"Usuario {user_id} ingresó cantidad: {cantidad}")
        
        if cantidad <= 0:
            await update.message.reply_text(
                "La cantidad debe ser mayor a cero. Por favor, ingresa un valor válido:"
            )
            return CANTIDAD
        
        datos_compra[user_id]["cantidad"] = cantidad
        
        tipo_cafe = datos_compra[user_id]["tipo_cafe"]
        proveedor = datos_compra[user_id]["proveedor"]
        
        await update.message.reply_text(
            f"Tipo de café: {tipo_cafe}\n"
            f"Proveedor: {proveedor}\n"
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
    """Guarda el precio y solicita confirmación"""
    user_id = update.effective_user.id
    try:
        precio = float(update.message.text.replace(',', '.'))
        logger.info(f"Usuario {user_id} ingresó precio: {precio}")
        
        if precio <= 0:
            await update.message.reply_text(
                "El precio debe ser mayor a cero. Por favor, ingresa un valor válido:"
            )
            return PRECIO
        
        datos_compra[user_id]["precio"] = precio
        
        # Calcular el total
        cantidad = datos_compra[user_id]["cantidad"]
        total = cantidad * precio
        datos_compra[user_id]["total"] = total
        
        # Mostrar resumen para confirmar
        compra = datos_compra[user_id]
        
        await update.message.reply_text(
            "📝 *Resumen de la compra*\n\n"
            f"Tipo de café: {compra['tipo_cafe']}\n"
            f"Proveedor: {compra['proveedor']}\n"
            f"Cantidad: {compra['cantidad']} kg\n"
            f"Precio: {precio} por kg\n"
            f"Total: {total}\n\n"
            "¿Confirmar esta compra? (Sí/No)",
            parse_mode="Markdown"
        )
        return CONFIRMAR
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para precio: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el precio."
        )
        return PRECIO

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
            # Llamar a la función para guardar los datos
            append_data(COMPRAS_FILE, compra, COMPRAS_HEADERS)
            
            logger.info(f"Compra guardada exitosamente para usuario {user_id}")
            
            await update.message.reply_text(
                "✅ ¡Compra registrada exitosamente!\n\n"
                f"Tipo: {compra['tipo_cafe']}\n"
                f"Proveedor: {compra['proveedor']}\n"
                f"Cantidad: {compra['cantidad']} kg\n"
                f"Precio: {compra['precio']} por kg\n"
                f"Total: {compra['total']}\n\n"
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
            TIPO_CAFE: [CallbackQueryHandler(tipo_cafe_callback, pattern=r'^tipo_')],
            PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handlers de compras registrados")