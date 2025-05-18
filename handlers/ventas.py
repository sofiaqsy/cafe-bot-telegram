import logging
import datetime
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from config import VENTAS_FILE
from utils.db import append_data
from utils.helpers import safe_float

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
CLIENTE, PRODUCTO, CANTIDAD, PRECIO, CONFIRMAR = range(5)

# Datos temporales
datos_venta = {}

# Headers para la hoja de ventas
VENTAS_HEADERS = ["fecha", "cliente", "producto", "cantidad", "precio", "total"]

# Productos disponibles (ejemplo)
productos = [
    "Café en grano", "Café molido", "Café premium", 
    "Café especial", "Café orgánico"
]

async def venta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de venta"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /venta")
    await update.message.reply_text(
        "Vamos a registrar una nueva venta de café.\n\n"
        "Por favor, ingresa el nombre del cliente:"
    )
    return CLIENTE

async def cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el cliente y solicita el producto"""
    user_id = update.effective_user.id
    cliente_nombre = update.message.text
    logger.info(f"Usuario {user_id} ingresó cliente: {cliente_nombre}")
    
    datos_venta[user_id] = {"cliente": cliente_nombre}
    
    # Crear mensaje con productos disponibles
    productos_msg = "Selecciona el producto vendido:\n\n"
    for i, prod in enumerate(productos, 1):
        productos_msg += f"{i} - {prod}\n"
    
    await update.message.reply_text(
        f"Cliente: {cliente_nombre}\n\n"
        f"{productos_msg}\n"
        "Ingresa el número correspondiente al producto:"
    )
    return PRODUCTO

async def producto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el producto y solicita la cantidad"""
    user_id = update.effective_user.id
    try:
        prod_num = int(update.message.text)
        
        if 1 <= prod_num <= len(productos):
            producto = productos[prod_num - 1]
            logger.info(f"Usuario {user_id} ingresó producto: {producto} ({prod_num})")
            
            datos_venta[user_id]["producto"] = producto
            
            await update.message.reply_text(
                f"Producto: {producto}\n\n"
                "Ahora, ingresa la cantidad vendida en kg:"
            )
            return CANTIDAD
        else:
            logger.warning(f"Usuario {user_id} ingresó un valor fuera de rango para producto: {prod_num}")
            await update.message.reply_text(
                f"Por favor, selecciona un número del 1 al {len(productos)} para el producto."
            )
            return PRODUCTO
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para producto: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el producto."
        )
        return PRODUCTO

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita el precio"""
    user_id = update.effective_user.id
    try:
        cantidad = safe_float(update.message.text)
        logger.info(f"Usuario {user_id} ingresó cantidad: {cantidad}")
        
        if cantidad <= 0:
            await update.message.reply_text(
                "La cantidad debe ser mayor que cero. Intenta nuevamente:"
            )
            return CANTIDAD
            
        datos_venta[user_id]["cantidad"] = cantidad
        
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
    """Guarda el precio y solicita confirmación"""
    user_id = update.effective_user.id
    try:
        precio = safe_float(update.message.text)
        logger.info(f"Usuario {user_id} ingresó precio: {precio}")
        
        if precio <= 0:
            await update.message.reply_text(
                "El precio debe ser mayor que cero. Intenta nuevamente:"
            )
            return PRECIO
            
        datos_venta[user_id]["precio"] = precio
        
        # Calcular el total
        venta = datos_venta[user_id]
        total = venta["cantidad"] * precio
        datos_venta[user_id]["total"] = total
        
        # Mostrar resumen para confirmar
        await update.message.reply_text(
            "📝 *Resumen de la venta*\n\n"
            f"Cliente: {venta['cliente']}\n"
            f"Producto: {venta['producto']}\n"
            f"Cantidad: {venta['cantidad']} kg\n"
            f"Precio por kg: {venta['precio']}\n"
            f"Total: {total}\n\n"
            "¿Confirmar esta venta? (Sí/No)",
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
    """Confirma y guarda la venta"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    logger.info(f"Usuario {user_id} respondió a confirmación: {respuesta}")
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Preparar datos para guardar
        venta = datos_venta[user_id].copy()
        
        # Añadir fecha
        venta["fecha"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Guardando venta en Google Sheets: {venta}")
        
        # Guardar la venta en Google Sheets
        try:
            append_data(VENTAS_FILE, venta, VENTAS_HEADERS)
            
            logger.info(f"Venta guardada exitosamente para usuario {user_id}")
            
            await update.message.reply_text(
                "✅ ¡Venta registrada exitosamente!\n\n"
                "Usa /venta para registrar otra venta."
            )
        except Exception as e:
            logger.error(f"Error al guardar venta: {e}")
            await update.message.reply_text(
                "❌ Error al guardar la venta. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}\n\n"
                "Contacta al administrador si el problema persiste."
            )
    else:
        logger.info(f"Usuario {user_id} canceló la venta")
        await update.message.reply_text(
            "❌ Venta cancelada.\n\n"
            "Usa /venta para iniciar de nuevo."
        )
    
    # Limpiar datos temporales
    if user_id in datos_venta:
        del datos_venta[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló el registro de venta con /cancelar")
    
    # Limpiar datos temporales
    if user_id in datos_venta:
        del datos_venta[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /venta para iniciar de nuevo cuando quieras."
    )
    
    return ConversationHandler.END

def register_ventas_handlers(application):
    """Registra los handlers para el módulo de ventas"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("venta", venta_command)],
        states={
            CLIENTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cliente)],
            PRODUCTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, producto)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handlers de ventas registrados")