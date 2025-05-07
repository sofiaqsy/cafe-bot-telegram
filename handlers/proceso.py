from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes

# Estados para la conversación
LOTE, ESTADO, CANTIDAD, NOTAS, CONFIRMAR = range(5)

# Datos temporales
datos_proceso = {}

async def proceso_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de procesamiento"""
    await update.message.reply_text(
        "Vamos a registrar un procesamiento de café.\n\n"
        "Por favor, ingresa el ID o nombre del lote a procesar:"
    )
    return LOTE

async def lote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el lote y solicita el estado del procesamiento"""
    user_id = update.effective_user.id
    datos_proceso[user_id] = {"lote": update.message.text}
    
    await update.message.reply_text(
        f"Lote: {update.message.text}\n\n"
        "Ahora, indica el estado al que pasará el café:\n"
        "1 - Despulpado\n"
        "2 - Fermentado\n"
        "3 - Lavado\n"
        "4 - Secado\n"
        "5 - Tostado\n"
        "6 - Molido\n"
        "7 - Empacado"
    )
    return ESTADO

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el estado y solicita la cantidad"""
    user_id = update.effective_user.id
    try:
        estado_num = int(update.message.text)
        estados = ["Despulpado", "Fermentado", "Lavado", "Secado", "Tostado", "Molido", "Empacado"]
        
        if 1 <= estado_num <= 7:
            estado_txt = estados[estado_num - 1]
            datos_proceso[user_id]["estado"] = estado_txt
            
            await update.message.reply_text(
                f"Estado: {estado_txt}\n\n"
                "Ingresa la cantidad de café a procesar (en kg):"
            )
            return CANTIDAD
        else:
            await update.message.reply_text(
                "Por favor, selecciona un número del 1 al 7 para el estado."
            )
            return ESTADO
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el estado."
        )
        return ESTADO

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita notas adicionales"""
    user_id = update.effective_user.id
    try:
        cantidad = float(update.message.text)
        datos_proceso[user_id]["cantidad"] = cantidad
        
        await update.message.reply_text(
            f"Cantidad: {cantidad} kg\n\n"
            "¿Alguna nota adicional sobre este proceso? (escribe 'ninguna' si no hay)"
        )
        return NOTAS
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un número válido para la cantidad."
        )
        return CANTIDAD

async def notas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda las notas y solicita confirmación"""
    user_id = update.effective_user.id
    notas_txt = update.message.text
    datos_proceso[user_id]["notas"] = notas_txt
    
    # Mostrar resumen para confirmar
    proceso = datos_proceso[user_id]
    
    await update.message.reply_text(
        "📝 *Resumen del proceso*\n\n"
        f"Lote: {proceso['lote']}\n"
        f"Estado: {proceso['estado']}\n"
        f"Cantidad: {proceso['cantidad']} kg\n"
        f"Notas: {proceso['notas']}\n\n"
        "¿Confirmar este proceso? (Sí/No)",
        parse_mode="Markdown"
    )
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda el proceso"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Aquí se guardaría el proceso en el CSV
        # Por ahora solo mostraremos un mensaje de éxito
        
        await update.message.reply_text(
            "✅ ¡Proceso registrado exitosamente!\n\n"
            "Usa /proceso para registrar otro proceso."
        )
    else:
        await update.message.reply_text(
            "❌ Proceso cancelado.\n\n"
            "Usa /proceso para iniciar de nuevo."
        )
    
    # Limpiar datos temporales
    if user_id in datos_proceso:
        del datos_proceso[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    
    # Limpiar datos temporales
    if user_id in datos_proceso:
        del datos_proceso[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /proceso para iniciar de nuevo cuando quieras."
    )
    
    return ConversationHandler.END

def register_proceso_handlers(application):
    """Registra los handlers para el módulo de proceso"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("proceso", proceso_command)],
        states={
            LOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, lote)],
            ESTADO: [MessageHandler(filters.TEXT & ~filters.COMMAND, estado)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
            NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, notas)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
