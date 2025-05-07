from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes

# Estados para la conversación
CONCEPTO, MONTO, CATEGORIA, NOTAS, CONFIRMAR = range(5)

# Datos temporales
datos_gasto = {}

# Categorías de gastos
categorias = [
    "Operativo", "Mantenimiento", "Transporte", 
    "Personal", "Insumos", "Servicios", "Otro"
]

async def gasto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de gasto"""
    await update.message.reply_text(
        "Vamos a registrar un nuevo gasto.\n\n"
        "Por favor, ingresa el concepto o descripción del gasto:"
    )
    return CONCEPTO

async def concepto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el concepto y solicita el monto"""
    user_id = update.effective_user.id
    datos_gasto[user_id] = {"concepto": update.message.text}
    
    await update.message.reply_text(
        f"Concepto: {update.message.text}\n\n"
        "Ahora, ingresa el monto del gasto (solo el número):"
    )
    return MONTO

async def monto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el monto y solicita la categoría"""
    user_id = update.effective_user.id
    try:
        monto = float(update.message.text)
        datos_gasto[user_id]["monto"] = monto
        
        # Crear mensaje con categorías disponibles
        categorias_msg = "Selecciona la categoría del gasto:\n\n"
        for i, cat in enumerate(categorias, 1):
            categorias_msg += f"{i} - {cat}\n"
        
        await update.message.reply_text(
            f"Monto: {monto}\n\n"
            f"{categorias_msg}"
        )
        return CATEGORIA
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un número válido para el monto."
        )
        return MONTO

async def categoria(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la categoría y solicita notas adicionales"""
    user_id = update.effective_user.id
    try:
        cat_num = int(update.message.text)
        
        if 1 <= cat_num <= len(categorias):
            categoria = categorias[cat_num - 1]
            datos_gasto[user_id]["categoria"] = categoria
            
            await update.message.reply_text(
                f"Categoría: {categoria}\n\n"
                "¿Alguna nota adicional sobre este gasto? (escribe 'ninguna' si no hay)"
            )
            return NOTAS
        else:
            await update.message.reply_text(
                f"Por favor, selecciona un número del 1 al {len(categorias)} para la categoría."
            )
            return CATEGORIA
    except ValueError:
        await update.message.reply_text(
            "Por favor, ingresa un número válido para la categoría."
        )
        return CATEGORIA

async def notas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda las notas y solicita confirmación"""
    user_id = update.effective_user.id
    notas_txt = update.message.text
    datos_gasto[user_id]["notas"] = notas_txt
    
    # Mostrar resumen para confirmar
    gasto = datos_gasto[user_id]
    
    await update.message.reply_text(
        "📝 *Resumen del gasto*\n\n"
        f"Concepto: {gasto['concepto']}\n"
        f"Monto: {gasto['monto']}\n"
        f"Categoría: {gasto['categoria']}\n"
        f"Notas: {gasto['notas']}\n\n"
        "¿Confirmar este gasto? (Sí/No)",
        parse_mode="Markdown"
    )
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda el gasto"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Aquí se guardaría el gasto en el CSV
        # Por ahora solo mostraremos un mensaje de éxito
        
        await update.message.reply_text(
            "✅ ¡Gasto registrado exitosamente!\n\n"
            "Usa /gasto para registrar otro gasto."
        )
    else:
        await update.message.reply_text(
            "❌ Gasto cancelado.\n\n"
            "Usa /gasto para iniciar de nuevo."
        )
    
    # Limpiar datos temporales
    if user_id in datos_gasto:
        del datos_gasto[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    
    # Limpiar datos temporales
    if user_id in datos_gasto:
        del datos_gasto[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /gasto para iniciar de nuevo cuando quieras."
    )
    
    return ConversationHandler.END

def register_gastos_handlers(application):
    """Registra los handlers para el módulo de gastos"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("gasto", gasto_command)],
        states={
            CONCEPTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, concepto)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto)],
            CATEGORIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, categoria)],
            NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, notas)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
