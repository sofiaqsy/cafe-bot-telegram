from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes

# Estados para la conversación
CLIENTE, PRODUCTO, CANTIDAD, PRECIO, CONFIRMAR = range(5)

# Datos temporales
datos_venta = {}

# Productos disponibles (ejemplo)
productos = [
    "Café en grano", "Café molido", "Café premium", 
    "Café especial", "Café orgánico"
]

async def venta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de venta"""
    await update.message.reply_text(
        "Vamos a registrar una nueva venta de café.\n\n"
        "Por favor, ingresa el nombre del cliente:"
    )
    return CLIENTE

async def cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el cliente y solicita el producto"""
    user_id = update.effective_user.id
    datos_venta[user_id] = {"cliente": update.message.text}
    
    # Crear mensaje con productos disponibles
    productos_msg = "Selecciona el producto vendido:\n\n"
    for i, prod in enumerate(productos, 1):
        productos_msg += f"{i} - {prod}\n"
    
    await update.message.reply_text(
        f"Cliente: {update.message.text}\n\n"
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
            datos_venta[user_id]["producto"] = producto
            
            await update.message.reply_text(
                f"Producto: {producto}\n\n"
                "Ahora, ingresa la cantidad vendida en kg:"
            )
            return CANTIDAD
        else:
            await update.message.reply_text(
                f"Por favor, selecciona un número del 1 al {len(productos)} para el producto."
            )
            return PRODUCTO
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el producto."
        )
        return PRODUCTO

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita el precio"""
    user_id = update.effective_user.id
    try:
        cantidad = float(update.message.text)
        datos_venta[user_id]["cantidad"] = cantidad
        
        await update.message.reply_text(
            f"Cantidad: {cantidad} kg\n\n"
            "Ahora, ingresa el precio por kg (solo el número):"
        )
        return PRECIO
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un número válido para la cantidad."
        )
        return CANTIDAD

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el precio y solicita confirmación"""
    user_id = update.effective_user.id
    try:
        precio = float(update.message.text)
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
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el precio."
        )
        return PRECIO

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda la venta"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Aquí se guardaría la venta en el CSV
        # Por ahora solo mostraremos un mensaje de éxito
        
        await update.message.reply_text(
            "✅ ¡Venta registrada exitosamente!\n\n"
            "Usa /venta para registrar otra venta."
        )
    else:
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
