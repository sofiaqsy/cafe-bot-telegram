import logging
import datetime
from telegram import Update
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from config import GASTOS_FILE
from utils.db import append_data

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
CONCEPTO, MONTO, CATEGORIA, NOTAS, CONFIRMAR = range(5)

# Datos temporales
datos_gasto = {}

# Headers para la hoja de gastos
GASTOS_HEADERS = ["fecha", "concepto", "monto", "categoria", "notas"]

# Categorías de gastos
categorias = [
    "Operativo", "Mantenimiento", "Transporte", 
    "Personal", "Insumos", "Servicios", "Otro"
]

async def gasto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de gasto"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /gasto")
    await update.message.reply_text(
        "Vamos a registrar un nuevo gasto.\n\n"
        "Por favor, ingresa el concepto o descripción del gasto:"
    )
    return CONCEPTO

async def concepto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el concepto y solicita el monto"""
    user_id = update.effective_user.id
    concepto_texto = update.message.text
    logger.info(f"Usuario {user_id} ingresó concepto: {concepto_texto}")
    
    datos_gasto[user_id] = {"concepto": concepto_texto}
    
    await update.message.reply_text(
        f"Concepto: {concepto_texto}\n\n"
        "Ahora, ingresa el monto del gasto (solo el número):"
    )
    return MONTO

async def monto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el monto y solicita la categoría"""
    user_id = update.effective_user.id
    try:
        monto = float(update.message.text)
        logger.info(f"Usuario {user_id} ingresó monto: {monto}")
        
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
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para monto: {update.message.text}")
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
            logger.info(f"Usuario {user_id} ingresó categoría: {categoria} ({cat_num})")
            
            datos_gasto[user_id]["categoria"] = categoria
            
            await update.message.reply_text(
                f"Categoría: {categoria}\n\n"
                "¿Alguna nota adicional sobre este gasto? (escribe 'ninguna' si no hay)"
            )
            return NOTAS
        else:
            logger.warning(f"Usuario {user_id} ingresó un valor fuera de rango para categoría: {cat_num}")
            await update.message.reply_text(
                f"Por favor, selecciona un número del 1 al {len(categorias)} para la categoría."
            )
            return CATEGORIA
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para categoría: {update.message.text}")
        await update.message.reply_text(
            "Por favor, ingresa un número válido para la categoría."
        )
        return CATEGORIA

async def notas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda las notas y solicita confirmación"""
    user_id = update.effective_user.id
    notas_txt = update.message.text
    logger.info(f"Usuario {user_id} ingresó notas: {notas_txt}")
    
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
    logger.info(f"Usuario {user_id} respondió a confirmación: {respuesta}")
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Preparar datos para guardar
        gasto = datos_gasto[user_id].copy()
        
        # Añadir fecha
        gasto["fecha"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"Guardando gasto en Google Sheets: {gasto}")
        
        # Guardar el gasto en Google Sheets
        try:
            append_data(GASTOS_FILE, gasto, GASTOS_HEADERS)
            
            logger.info(f"Gasto guardado exitosamente para usuario {user_id}")
            
            await update.message.reply_text(
                "✅ ¡Gasto registrado exitosamente!\n\n"
                "Usa /gasto para registrar otro gasto."
            )
        except Exception as e:
            logger.error(f"Error al guardar gasto: {e}")
            await update.message.reply_text(
                "❌ Error al guardar el gasto. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}\n\n"
                "Contacta al administrador si el problema persiste."
            )
    else:
        logger.info(f"Usuario {user_id} canceló el gasto")
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
    logger.info(f"Usuario {user_id} canceló el registro de gasto con /cancelar")
    
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
    logger.info("Handlers de gastos registrados")