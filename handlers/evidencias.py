"""
Manejador para el comando /evidencia.
Este comando es un alias simplificado del comando /documento,
específicamente para que sea más intuitivo para los usuarios.
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from handlers.documents import documento_command, registro_documento, SUBIR_DOCUMENTO, register_documents_handlers
from utils.sheets import get_all_data
from utils.helpers import get_now_peru

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_COMPRA = 0

# Datos temporales
datos_evidencia = {}

async def evidencia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Comando /evidencia para mostrar una lista seleccionable de compras registradas
    para adjuntar evidencias de pago
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /evidencia INICIADO por {username} (ID: {user_id}) ===")
    
    # Inicializar datos para este usuario
    datos_evidencia[user_id] = {}
    
    # Mostrar las compras recientes en un teclado seleccionable
    try:
        compras = get_all_data('compras')
        if compras:
            # Ordenar las compras por fecha (más recientes primero)
            compras_recientes = sorted(compras, key=lambda x: x.get('fecha', ''), reverse=True)[:10]
            
            # Crear teclado con las compras
            keyboard = []
            for compra in compras_recientes:
                compra_id = compra.get('id', 'Sin ID')
                proveedor = compra.get('proveedor', 'Proveedor desconocido')
                tipo_cafe = compra.get('tipo_cafe', 'Tipo desconocido')
                
                # Formatear fecha sin hora (solo YYYY-MM-DD)
                fecha_completa = compra.get('fecha', '')
                fecha_corta = fecha_completa.split(' ')[0] if ' ' in fecha_completa else fecha_completa
                
                # Crear botón con el formato: proveedor, tipo_cafe, fecha(sin hora), id
                boton_text = f"{proveedor}, {tipo_cafe}, '{fecha_corta}, {compra_id}"
                keyboard.append([boton_text])
            
            keyboard.append(["❌ Cancelar"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            mensaje = "📋 *SELECCIONA UNA COMPRA PARA ADJUNTAR EVIDENCIA DE PAGO*\n\n"
            mensaje += "Formato: proveedor, tipo de café, fecha, ID"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
            
            # Redirigir al estado de selección de compra
            return SELECCIONAR_COMPRA
        else:
            await update.message.reply_text(
                "No hay compras registradas. Usa /compra para registrar una nueva compra.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error al obtener compras: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al obtener las compras. Por favor, intenta nuevamente o usa /documento directamente.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

async def seleccionar_compra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de compra por el usuario"""
    user_id = update.effective_user.id
    respuesta = update.message.text.strip()
    
    # Verificar si el usuario cancela
    if respuesta.lower() == "❌ cancelar":
        await update.message.reply_text("Operación cancelada. Usa /evidencia para iniciar nuevamente.")
        return ConversationHandler.END
    
    # Extraer el ID de la compra (que está al final de la línea después de la última coma)
    partes = respuesta.split(',')
    if len(partes) < 4:
        await update.message.reply_text(
            "❌ Formato de selección inválido. Por favor, usa /evidencia para intentar nuevamente.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    compra_id = partes[-1].strip()
    logger.info(f"Usuario {user_id} seleccionó compra con ID: {compra_id}")
    
    # Informar al usuario que se ha seleccionado correctamente la compra
    await update.message.reply_text(
        f"Has seleccionado la compra con ID: {compra_id}\n\n"
        f"Ahora, envía la imagen de la evidencia de pago.\n"
        f"La imagen debe ser clara y legible."
    )
    
    # Redirección al flujo de documentos para subir la evidencia
    logger.info(f"Redirigiendo al flujo de /documento con tipo COMPRA y ID {compra_id}")
    
    # Guardar datos en el contexto para pasarlos a la función registro_documento
    context.user_data["tipo_operacion"] = "COMPRA"
    context.user_data["operacion_id"] = compra_id
    
    # Iniciar el proceso de carga de documentos directamente
    return await registro_documento(update, context)

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela el proceso de evidencia"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló el proceso de evidencia")
    
    # Limpiar datos temporales
    if user_id in datos_evidencia:
        del datos_evidencia[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /evidencia para iniciar de nuevo cuando quieras."
    )
    
    return ConversationHandler.END

def register_evidencias_handlers(application):
    """Registra los handlers para el módulo de evidencias"""
    # Crear un handler de conversación específico para evidencias
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("evidencia", evidencia_command)],
        states={
            SELECCIONAR_COMPRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_compra)],
            # Agregar el estado SUBIR_DOCUMENTO para que el ConversationHandler lo reconozca
            SUBIR_DOCUMENTO: [MessageHandler(filters.PHOTO, lambda update, context: None)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handler de evidencias registrado")
