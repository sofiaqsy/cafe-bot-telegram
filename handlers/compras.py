import logging
import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from config import COMPRAS_FILE
from utils.db import append_data
from utils.helpers import get_now_peru, safe_float

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación - orden cambiado para pedir tipo_cafe primero
TIPO_CAFE, PROVEEDOR, CANTIDAD, PRECIO, CONFIRMAR = range(5)

# Datos temporales
datos_compra = {}

# Headers para la hoja de compras - actualizado para incluir fase_actual y kg_disponibles
COMPRAS_HEADERS = ["fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "total", "fase_actual", "kg_disponibles"]

# Tipos de café predefinidos - solo 3 opciones fijas
TIPOS_CAFE = ["CEREZO", "MOTE", "PERGAMINO"]

async def compra_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de compra solicitando primero el tipo de café"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} inició comando /compra")
    
    # Inicializar datos de compra para este usuario
    datos_compra[user_id] = {}
    
    # Crear teclado con las 3 opciones predefinidas para tipo de café
    keyboard = [[tipo] for tipo in TIPOS_CAFE]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "Vamos a registrar una nueva compra de café.\n\n"
        "Selecciona el tipo de café:",
        reply_markup=reply_markup
    )
    return TIPO_CAFE

async def tipo_cafe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de café y solicita el proveedor"""
    user_id = update.effective_user.id
    selected_tipo = update.message.text.strip().upper()
    
    # Verificar que sea uno de los tipos permitidos
    if selected_tipo not in TIPOS_CAFE:
        # Si no es un tipo válido, volver a mostrar las opciones
        keyboard = [[tipo] for tipo in TIPOS_CAFE]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Tipo de café no válido. Por favor, selecciona una de las opciones disponibles:",
            reply_markup=reply_markup
        )
        return TIPO_CAFE
    
    # Guardar el tipo de café
    logger.info(f"Usuario {user_id} seleccionó tipo de café: {selected_tipo}")
    datos_compra[user_id]["tipo_cafe"] = selected_tipo
    
    # Solicitar el proveedor
    await update.message.reply_text(
        f"Tipo de café: {selected_tipo}\n\n"
        "Ahora, ingresa el nombre del proveedor:",
        reply_markup=ReplyKeyboardRemove()
    )
    return PROVEEDOR

async def proveedor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el proveedor y solicita la cantidad"""
    user_id = update.effective_user.id
    proveedor_nombre = update.message.text.strip()
    logger.info(f"Usuario {user_id} ingresó proveedor: {proveedor_nombre}")
    
    # Verificar que no esté vacío
    if not proveedor_nombre:
        await update.message.reply_text(
            "Por favor, ingresa un nombre de proveedor válido."
        )
        return PROVEEDOR
    
    datos_compra[user_id]["proveedor"] = proveedor_nombre
    
    await update.message.reply_text(
        f"Proveedor: {proveedor_nombre}\n\n"
        "Ahora, ingresa la cantidad de café en kg:"
    )
    return CANTIDAD

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita el precio"""
    user_id = update.effective_user.id
    try:
        cantidad = safe_float(update.message.text)
        logger.info(f"Usuario {user_id} ingresó cantidad: {cantidad}")
        
        if cantidad <= 0:
            await update.message.reply_text("La cantidad debe ser mayor que cero. Intenta nuevamente:")
            return CANTIDAD
        
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
    """Guarda el precio y solicita confirmación"""
    user_id = update.effective_user.id
    try:
        precio = safe_float(update.message.text)
        logger.info(f"Usuario {user_id} ingresó precio: {precio}")
        
        if precio <= 0:
            await update.message.reply_text("El precio debe ser mayor que cero. Intenta nuevamente:")
            return PRECIO
        
        datos_compra[user_id]["precio"] = precio
        
        # Calcular el total
        compra = datos_compra[user_id]
        total = compra["cantidad"] * compra["precio"]
        
        # Guardar el total en los datos
        datos_compra[user_id]["total"] = total
        
        # Inicializar fase_actual con el tipo de café
        datos_compra[user_id]["fase_actual"] = compra["tipo_cafe"]
        
        # Inicializar kg_disponibles con la cantidad total
        datos_compra[user_id]["kg_disponibles"] = compra["cantidad"]
        
        # Crear teclado para confirmación
        keyboard = [["Sí", "No"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Mostrar resumen para confirmar
        await update.message.reply_text(
            "📝 *RESUMEN DE LA COMPRA*\n\n"
            f"Tipo de café: {compra['tipo_cafe']}\n"
            f"Proveedor: {compra['proveedor']}\n"
            f"Cantidad: {compra['cantidad']} kg\n"
            f"Precio: {compra['precio']} por kg\n"
            f"Total: {total}\n\n"
            "¿Confirmar esta compra?",
            parse_mode="Markdown",
            reply_markup=reply_markup
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
        
        # Añadir fecha actualizada
        now = get_now_peru()
        compra["fecha"] = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Verificar que todos los datos requeridos estén presentes
        campos_requeridos = ["tipo_cafe", "proveedor", "cantidad", "precio", "total", "fase_actual", "kg_disponibles"]
        datos_completos = all(campo in compra for campo in campos_requeridos)
        
        if not datos_completos:
            campos_faltantes = [campo for campo in campos_requeridos if campo not in compra]
            logger.error(f"Datos incompletos para usuario {user_id}. Campos faltantes: {campos_faltantes}. Datos: {compra}")
            await update.message.reply_text(
                "❌ Error: Datos incompletos. Por favor, inicia el proceso nuevamente con /compra.",
                reply_markup=ReplyKeyboardRemove()
            )
            if user_id in datos_compra:
                del datos_compra[user_id]
            return ConversationHandler.END
        
        logger.info(f"Guardando compra en Google Sheets: {compra}")
        
        # Guardar la compra en Google Sheets a través de db.py
        try:
            # Llamar a la función para guardar los datos
            result = append_data(COMPRAS_FILE, compra, COMPRAS_HEADERS)
            
            if result:
                logger.info(f"Compra guardada exitosamente para usuario {user_id}")
                
                await update.message.reply_text(
                    "✅ ¡Compra registrada exitosamente!\n\n"
                    "Usa /compra para registrar otra compra.",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                logger.error(f"Error al guardar compra: La función append_data devolvió False")
                await update.message.reply_text(
                    "❌ Error al guardar la compra. Por favor, intenta nuevamente.\n\n"
                    "Contacta al administrador si el problema persiste.",
                    reply_markup=ReplyKeyboardRemove()
                )
        except Exception as e:
            logger.error(f"Error al guardar compra: {e}")
            await update.message.reply_text(
                "❌ Error al guardar la compra. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}\n\n"
                "Contacta al administrador si el problema persiste.",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        logger.info(f"Usuario {user_id} canceló la compra")
        await update.message.reply_text(
            "❌ Compra cancelada.\n\n"
            "Usa /compra para iniciar de nuevo.",
            reply_markup=ReplyKeyboardRemove()
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
        "Usa /compra para iniciar de nuevo cuando quieras.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def register_compras_handlers(application):
    """Registra los handlers para el módulo de compras"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compra", compra_command)],
        states={
            TIPO_CAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_cafe)],
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