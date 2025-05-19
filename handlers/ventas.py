import logging
import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from config import VENTAS_FILE
from utils.db import append_data
from utils.helpers import safe_float
from utils.sheets import get_almacen_cantidad, FASES_CAFE, update_almacen

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_TIPO, CLIENTE, CANTIDAD, PRECIO, CONFIRMAR = range(5)

# Datos temporales
datos_venta = {}

# Headers para la hoja de ventas
VENTAS_HEADERS = ["fecha", "cliente", "tipo_cafe", "cantidad", "precio", "total", "ultima_actualizacion", "actualizado_por", "creado_por"]

async def venta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de venta"""
    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name
    
    logger.info(f"Usuario {user_id} inició comando /venta")
    
    # Limpiar datos previos
    if user_id in datos_venta:
        del datos_venta[user_id]
    
    # Crear registro temporal para esta venta
    datos_venta[user_id] = {"creado_por": user_name}
    
    # Obtener tipos de café disponibles en el almacén
    tipos_disponibles = []
    mensaje = "🛒 REGISTRAR VENTA\n\nSelecciona el tipo de café a vender:\n"
    
    for fase in FASES_CAFE:
        # No incluir CEREZO como se especificó en los requisitos
        if fase == "CEREZO":
            continue
            
        cantidad = get_almacen_cantidad(fase)
        if cantidad > 0:
            tipos_disponibles.append(f"{fase} ({cantidad} kg)")
            mensaje += f"• {fase}: {cantidad} kg disponibles\n"
    
    if not tipos_disponibles:
        await update.message.reply_text(
            "❌ No hay suficiente café disponible para vender.\n\n"
            "Usa el comando /almacen para verificar el inventario."
        )
        return ConversationHandler.END
    
    # Crear teclado con las opciones disponibles
    keyboard = [[tipo] for tipo in tipos_disponibles]
    keyboard.append(["❌ Cancelar"])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        mensaje + "\nPor favor, selecciona el tipo de café a vender:",
        reply_markup=reply_markup
    )
    
    return SELECCIONAR_TIPO

async def seleccionar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de café y solicita el cliente"""
    user_id = update.effective_user.id
    respuesta = update.message.text
    
    if respuesta == "❌ Cancelar":
        if user_id in datos_venta:
            del datos_venta[user_id]
        await update.message.reply_text(
            "❌ Operación cancelada.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Extraer solo el tipo de café (sin la parte de cantidad)
    tipo_cafe = respuesta.split(" (")[0].strip()
    
    # Verificar que sea un tipo válido
    if tipo_cafe not in FASES_CAFE or tipo_cafe == "CEREZO":
        await update.message.reply_text(
            "⚠️ Tipo de café no válido. Por favor, selecciona una opción de la lista.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Guardar el tipo seleccionado
    datos_venta[user_id]["tipo_cafe"] = tipo_cafe
    
    # Obtener la cantidad disponible para mostrarla
    cantidad_disponible = get_almacen_cantidad(tipo_cafe)
    datos_venta[user_id]["cantidad_disponible"] = cantidad_disponible
    
    logger.info(f"Usuario {user_id} seleccionó tipo de café: {tipo_cafe} (Disponible: {cantidad_disponible} kg)")
    
    await update.message.reply_text(
        f"Has seleccionado: {tipo_cafe} (Disponible: {cantidad_disponible} kg)\n\n"
        "Por favor, ingresa el nombre del cliente:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return CLIENTE

async def cliente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el cliente y solicita la cantidad"""
    user_id = update.effective_user.id
    cliente_nombre = update.message.text
    
    # Verificar que el nombre del cliente no esté vacío
    if not cliente_nombre or cliente_nombre.strip() == "":
        await update.message.reply_text(
            "⚠️ El nombre del cliente no puede estar vacío. Por favor, ingresa un nombre válido:"
        )
        return CLIENTE
    
    logger.info(f"Usuario {user_id} ingresó cliente: {cliente_nombre}")
    
    datos_venta[user_id]["cliente"] = cliente_nombre
    tipo_cafe = datos_venta[user_id]["tipo_cafe"]
    cantidad_disponible = datos_venta[user_id]["cantidad_disponible"]
    
    await update.message.reply_text(
        f"Cliente: {cliente_nombre}\n"
        f"Tipo de café: {tipo_cafe}\n\n"
        f"Cantidad disponible: {cantidad_disponible} kg\n\n"
        "Ingresa la cantidad a vender en kg:"
    )
    
    return CANTIDAD

async def cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y solicita el precio"""
    user_id = update.effective_user.id
    
    try:
        cantidad = safe_float(update.message.text)
        
        # Validar que la cantidad sea mayor que cero
        if cantidad <= 0:
            await update.message.reply_text(
                "⚠️ La cantidad debe ser mayor que cero. Intenta nuevamente:"
            )
            return CANTIDAD
        
        # Validar que haya suficiente cantidad disponible
        cantidad_disponible = datos_venta[user_id]["cantidad_disponible"]
        
        if cantidad > cantidad_disponible:
            await update.message.reply_text(
                f"⚠️ La cantidad solicitada ({cantidad} kg) es mayor que la disponible ({cantidad_disponible} kg).\n\n"
                "Por favor, ingresa una cantidad menor o igual a la disponible:"
            )
            return CANTIDAD
        
        logger.info(f"Usuario {user_id} ingresó cantidad: {cantidad} kg")
        
        datos_venta[user_id]["cantidad"] = cantidad
        
        await update.message.reply_text(
            f"Cantidad: {cantidad} kg\n\n"
            "Ahora, ingresa el precio por kg (solo el número):"
        )
        
        return PRECIO
        
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para cantidad: {update.message.text}")
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para la cantidad."
        )
        return CANTIDAD

async def precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el precio y solicita confirmación"""
    user_id = update.effective_user.id
    
    try:
        precio = safe_float(update.message.text)
        
        # Validar que el precio sea mayor que cero
        if precio <= 0:
            await update.message.reply_text(
                "⚠️ El precio debe ser mayor que cero. Intenta nuevamente:"
            )
            return PRECIO
        
        logger.info(f"Usuario {user_id} ingresó precio: {precio}")
        
        datos_venta[user_id]["precio"] = precio
        
        # Calcular el total
        venta = datos_venta[user_id]
        total = venta["cantidad"] * precio
        datos_venta[user_id]["total"] = total
        
        # Crear teclado para confirmación
        keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Mostrar resumen para confirmar
        await update.message.reply_text(
            "📝 *RESUMEN DE LA VENTA*\n\n"
            f"Cliente: {venta['cliente']}\n"
            f"Tipo de café: {venta['tipo_cafe']}\n"
            f"Cantidad: {venta['cantidad']} kg\n"
            f"Precio por kg: {venta['precio']}\n"
            f"Total: {total}\n\n"
            "¿Confirmar esta venta?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        return CONFIRMAR
    
    except ValueError:
        logger.warning(f"Usuario {user_id} ingresó un valor inválido para precio: {update.message.text}")
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para el precio."
        )
        return PRECIO

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda la venta"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    
    if user_id not in datos_venta:
        await update.message.reply_text(
            "❌ Ha ocurrido un error con los datos de la venta. Por favor, inicia nuevamente con /venta.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    logger.info(f"Usuario {user_id} respondió a confirmación: {respuesta}")
    
    if respuesta in ["✅ confirmar", "confirmar", "sí", "si", "s", "yes", "y"]:
        # Preparar datos para guardar
        venta = datos_venta[user_id].copy()
        
        # Añadir fecha y hora actuales
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        venta["fecha"] = ahora
        venta["ultima_actualizacion"] = ahora
        venta["actualizado_por"] = venta["creado_por"]
        
        # Eliminar datos temporales que no van a la base de datos
        if "cantidad_disponible" in venta:
            del venta["cantidad_disponible"]
        
        logger.info(f"Guardando venta en sistema: {venta}")
        
        try:
            # 1. Guardar la venta en la hoja correspondiente
            append_data(VENTAS_FILE, venta, VENTAS_HEADERS)
            
            # 2. Actualizar el almacén (restar la cantidad vendida)
            tipo_cafe = venta["tipo_cafe"]
            cantidad = venta["cantidad"]
            
            resultado_almacen = update_almacen(
                fase=tipo_cafe,
                cantidad_cambio=cantidad,
                operacion="restar",
                notas=f"Venta a cliente: {venta['cliente']}",
            )
            
            if resultado_almacen:
                logger.info(f"Almacén actualizado correctamente tras venta de {cantidad} kg de {tipo_cafe}")
            else:
                logger.error(f"Error al actualizar almacén tras venta de {cantidad} kg de {tipo_cafe}")
            
            # Mensaje de éxito
            await update.message.reply_text(
                "✅ ¡Venta registrada exitosamente!\n\n"
                f"Cliente: {venta['cliente']}\n"
                f"Tipo de café: {venta['tipo_cafe']}\n"
                f"Cantidad: {venta['cantidad']} kg\n"
                f"Total: {venta['total']}\n\n"
                "El almacén ha sido actualizado automáticamente.\n\n"
                "Usa /venta para registrar otra venta o /almacen para verificar el inventario.",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            logger.error(f"Error al guardar venta: {e}")
            await update.message.reply_text(
                "❌ Error al guardar la venta. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}\n\n"
                "Contacta al administrador si el problema persiste.",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        logger.info(f"Usuario {user_id} canceló la venta")
        await update.message.reply_text(
            "❌ Venta cancelada.\n\n"
            "Usa /venta para iniciar de nuevo.",
            reply_markup=ReplyKeyboardRemove()
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
        "Usa /venta para iniciar de nuevo cuando quieras.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def register_ventas_handlers(application):
    """Registra los handlers para el módulo de ventas"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("venta", venta_command)],
        states={
            SELECCIONAR_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_tipo)],
            CLIENTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cliente)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handlers de ventas registrados")