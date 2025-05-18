import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ConversationHandler, CallbackQueryHandler, ContextTypes
from utils.sheets import sincronizar_almacen_con_compras, FASES_CAFE, get_almacen_cantidad

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
CONFIRMAR = 0

async def sincronizar_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando para sincronizar manualmente el almacén con las compras"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} inició comando /sincronizar")
    
    # Crear teclado de confirmación
    keyboard = [
        [InlineKeyboardButton("✅ Sí, sincronizar almacén", callback_data="confirmar_sincronizacion")],
        [InlineKeyboardButton("❌ No, cancelar", callback_data="cancelar_sincronizacion")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚠️ SINCRONIZACIÓN DEL ALMACÉN\n\n"
        "Este proceso buscará compras existentes en el sistema y creará los registros correspondientes en el almacén.\n\n"
        "Se recomienda ejecutar este comando si:\n"
        "- No se muestran datos correctos en el almacén\n"
        "- Hay errores al ver las fases disponibles\n"
        "- Se han agregado compras nuevas recientemente\n\n"
        "¿Desea continuar con la sincronización?",
        reply_markup=reply_markup
    )
    return CONFIRMAR

async def procesar_sincronizacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la respuesta a la sincronización"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirmar_sincronizacion":
        await query.edit_message_text("🔄 Sincronizando almacén con las compras existentes...")
        
        # Ejecutar sincronización
        result = sincronizar_almacen_con_compras()
        
        if result:
            # Obtener cantidades actuales para informar
            cantidades = {}
            for fase in FASES_CAFE:
                cantidad = get_almacen_cantidad(fase)
                cantidades[fase] = cantidad
            
            # Formatear mensaje de éxito
            mensaje = "✅ Sincronización completada exitosamente\n\n"
            mensaje += "📊 CANTIDADES ACTUALES EN ALMACÉN:\n"
            for fase, cantidad in cantidades.items():
                mensaje += f"- {fase}: {cantidad} kg\n"
            
            await query.edit_message_text(mensaje)
        else:
            await query.edit_message_text(
                "❌ Error al sincronizar el almacén\n\n"
                "Hubo un problema durante la sincronización. Por favor, revisa los logs del sistema "
                "o contacta al administrador para solucionar el problema."
            )
    else:
        await query.edit_message_text("❌ Sincronización cancelada.")
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación de sincronización"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló la sincronización")
    
    await update.message.reply_text("❌ Sincronización cancelada.")
    return ConversationHandler.END

def register_sincronizar_handlers(application):
    """Registra los manejadores para el comando de sincronización"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("sincronizar", sincronizar_command)],
        states={
            CONFIRMAR: [CallbackQueryHandler(procesar_sincronizacion)]
        },
        fallbacks=[CommandHandler("cancelar", cancelar)]
    )
    
    # Agregar el manejador a la aplicación
    application.add_handler(conv_handler)
    logger.info("Handlers de sincronización registrados")