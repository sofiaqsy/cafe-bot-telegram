import logging
import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler, ConversationHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler
)
from utils.sheets import (
    get_all_data, get_filtered_data, update_cell, 
    FASES_CAFE, get_almacen_cantidad, update_almacen,
    sincronizar_almacen_con_compras
)
from utils.helpers import format_currency, safe_float

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_ACCION, SELECCIONAR_FASE, INGRESAR_CANTIDAD, CONFIRMAR_ACTUALIZACION = range(4)

async def almacen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el comando de gestión de almacén"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /almacen")
    
    # Limpiar datos previos
    context.user_data.clear()
    
    # Mostrar el estado actual del almacén
    almacen_data = get_filtered_data('almacen')
    
    mensaje = "📦 ALMACÉN CENTRAL DE CAFÉ\n\n"
    
    if not almacen_data:
        mensaje += "No hay información en el almacén. Se recomienda sincronizar con las compras."
    else:
        mensaje += "📊 INVENTARIO ACTUAL:\n"
        for fase in FASES_CAFE:
            cantidad = get_almacen_cantidad(fase)
            mensaje += f"• {fase}: {cantidad} kg\n"
    
    # Opciones disponibles
    keyboard = [
        ["📊 Ver inventario"],
        ["🔄 Sincronizar con compras"],
        ["📝 Actualizar manualmente"],
        ["❌ Cancelar"]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        mensaje + "\n\n¿Qué acción deseas realizar?",
        reply_markup=reply_markup
    )
    
    return SELECCIONAR_ACCION

async def seleccionar_accion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de acción del usuario"""
    accion = update.message.text
    
    if accion == "📊 Ver inventario":
        return await mostrar_inventario(update, context)
    
    elif accion == "🔄 Sincronizar con compras":
        return await iniciar_sincronizacion(update, context)
    
    elif accion == "📝 Actualizar manualmente":
        # Crear teclado con fases disponibles
        keyboard = []
        for fase in FASES_CAFE:
            # Obtener cantidad actual
            cantidad = get_almacen_cantidad(fase)
            keyboard.append([f"{fase} ({cantidad} kg)"])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "Selecciona la fase que deseas actualizar:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_FASE
    
    elif accion == "❌ Cancelar":
        await update.message.reply_text(
            "Operación cancelada.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    else:
        keyboard = [
            ["📊 Ver inventario"],
            ["🔄 Sincronizar con compras"],
            ["📝 Actualizar manualmente"],
            ["❌ Cancelar"]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            "Por favor, selecciona una opción válida:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_ACCION

async def mostrar_inventario(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el inventario actual detallado"""
    
    # Obtener datos del almacén
    almacen_data = get_filtered_data('almacen')
    
    if not almacen_data:
        await update.message.reply_text(
            "📦 ALMACÉN CENTRAL DE CAFÉ\n\n"
            "No hay información en el almacén. Se recomienda sincronizar con las compras.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        mensaje = "📦 INVENTARIO DETALLADO DEL ALMACÉN\n\n"
        
        # Mostrar cada fase con su cantidad
        for fase in FASES_CAFE:
            # Buscar en almacen_data
            fase_data = None
            for item in almacen_data:
                if item.get('fase', '').strip().upper() == fase:
                    fase_data = item
                    break
            
            if fase_data:
                cantidad = safe_float(fase_data.get('cantidad', 0))
                ultima_actualizacion = fase_data.get('ultima_actualizacion', 'Desconocida')
                
                mensaje += f"🔹 {fase}: {cantidad} kg\n"
                mensaje += f"   Última actualización: {ultima_actualizacion}\n"
            else:
                mensaje += f"🔹 {fase}: 0 kg (No registrado)\n"
        
        # Información adicional
        mensaje += "\nLa sincronización con compras asegura que el almacén refleje con precisión las existencias actuales."
        
        keyboard = [
            ["📊 Ver inventario"],
            ["🔄 Sincronizar con compras"],
            ["📝 Actualizar manualmente"],
            ["❌ Cancelar"]
        ]
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            mensaje,
            reply_markup=reply_markup
        )
    
    return SELECCIONAR_ACCION

async def iniciar_sincronizacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de sincronización con compras"""
    
    await update.message.reply_text(
        "🔄 Sincronizando almacén con compras...\n"
        "Este proceso puede tardar unos segundos.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    try:
        # Llamar a la función de sincronización
        resultado = sincronizar_almacen_con_compras()
        
        if resultado:
            # Obtener los nuevos valores del almacén
            mensaje = "✅ Sincronización completada correctamente.\n\n"
            mensaje += "📊 INVENTARIO ACTUALIZADO:\n"
            
            for fase in FASES_CAFE:
                cantidad = get_almacen_cantidad(fase)
                mensaje += f"• {fase}: {cantidad} kg\n"
            
            await update.message.reply_text(
                mensaje,
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                "❌ Error durante la sincronización. Por favor, inténtalo nuevamente.",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as e:
        logger.error(f"Error al sincronizar almacén: {e}")
        await update.message.reply_text(
            f"❌ Error durante la sincronización: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
    
    return ConversationHandler.END

async def seleccionar_fase(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de fase para actualización manual"""
    
    # Extraer solo el nombre de la fase (eliminar la parte de la cantidad si existe)
    texto_fase = update.message.text.strip()
    fase = texto_fase.split(" (")[0].strip().upper()
    
    # Verificar que la fase sea válida
    if fase not in FASES_CAFE:
        # Mostrar error y regresar a selección de fase
        keyboard = []
        for f in FASES_CAFE:
            cantidad = get_almacen_cantidad(f)
            keyboard.append([f"{f} ({cantidad} kg)"])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "⚠️ Fase no válida. Por favor, selecciona una fase de la lista:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_FASE
    
    # Guardar la fase seleccionada
    context.user_data['fase'] = fase
    
    # Obtener la cantidad actual
    cantidad_actual = get_almacen_cantidad(fase)
    context.user_data['cantidad_actual'] = cantidad_actual
    
    # Solicitar nueva cantidad
    await update.message.reply_text(
        f"La fase {fase} actualmente tiene {cantidad_actual} kg en el almacén.\n\n"
        "Introduce la nueva cantidad (en kg) o el ajuste:\n"
        "• Para establecer una cantidad exacta, introduce el número.\n"
        "• Para sumar, introduce + seguido del número (ej: +10.5)\n"
        "• Para restar, introduce - seguido del número (ej: -5.2)",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return INGRESAR_CANTIDAD

async def ingresar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la cantidad ingresada para actualización del almacén"""
    
    texto = update.message.text.strip()
    fase = context.user_data['fase']
    cantidad_actual = context.user_data['cantidad_actual']
    
    # Determinar la operación
    if texto.startswith('+'):
        # Sumar
        try:
            cantidad_cambio = float(texto[1:].strip())
            nueva_cantidad = cantidad_actual + cantidad_cambio
            operacion = "sumar"
            mensaje_operacion = f"Sumar {cantidad_cambio} kg"
        except ValueError:
            await update.message.reply_text(
                "⚠️ Formato inválido. Introduce un número válido para sumar (ej: +10.5)."
            )
            return INGRESAR_CANTIDAD
    
    elif texto.startswith('-'):
        # Restar
        try:
            cantidad_cambio = float(texto[1:].strip())
            nueva_cantidad = max(0, cantidad_actual - cantidad_cambio)  # Nunca menor a 0
            operacion = "restar"
            mensaje_operacion = f"Restar {cantidad_cambio} kg"
        except ValueError:
            await update.message.reply_text(
                "⚠️ Formato inválido. Introduce un número válido para restar (ej: -5.2)."
            )
            return INGRESAR_CANTIDAD
    
    else:
        # Establecer valor exacto
        try:
            nueva_cantidad = float(texto)
            cantidad_cambio = nueva_cantidad
            operacion = "establecer"
            mensaje_operacion = f"Establecer cantidad exacta de {nueva_cantidad} kg"
        except ValueError:
            await update.message.reply_text(
                "⚠️ Formato inválido. Introduce un número válido."
            )
            return INGRESAR_CANTIDAD
    
    # Guardar datos para confirmación
    context.user_data['nueva_cantidad'] = nueva_cantidad
    context.user_data['cantidad_cambio'] = cantidad_cambio
    context.user_data['operacion'] = operacion
    
    # Solicitar confirmación
    keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        f"📝 RESUMEN DE ACTUALIZACIÓN:\n\n"
        f"Fase: {fase}\n"
        f"Cantidad actual: {cantidad_actual} kg\n"
        f"Operación: {mensaje_operacion}\n"
        f"Nueva cantidad: {nueva_cantidad} kg\n\n"
        "¿Confirmas esta actualización?",
        reply_markup=reply_markup
    )
    
    return CONFIRMAR_ACTUALIZACION

async def confirmar_actualizacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y ejecuta la actualización del almacén"""
    
    respuesta = update.message.text.strip()
    
    if respuesta == "✅ Confirmar":
        fase = context.user_data['fase']
        operacion = context.user_data['operacion']
        cantidad_cambio = context.user_data['cantidad_cambio']
        nueva_cantidad = context.user_data['nueva_cantidad']
        
        # Registrar quién hizo la modificación
        usuario = update.effective_user.username or update.effective_user.first_name
        notas = f"Actualización manual por {usuario}"
        
        try:
            # Actualizar el almacén
            resultado = update_almacen(
                fase=fase,
                cantidad_cambio=cantidad_cambio,
                operacion=operacion,
                notas=notas
            )
            
            if resultado:
                await update.message.reply_text(
                    f"✅ Almacén actualizado correctamente.\n\n"
                    f"Fase: {fase}\n"
                    f"Nueva cantidad: {nueva_cantidad} kg",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                await update.message.reply_text(
                    "❌ Error al actualizar el almacén. Por favor, inténtalo nuevamente.",
                    reply_markup=ReplyKeyboardRemove()
                )
        except Exception as e:
            logger.error(f"Error al actualizar almacén: {e}")
            await update.message.reply_text(
                f"❌ Error al actualizar el almacén: {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await update.message.reply_text(
            "❌ Actualización cancelada.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Limpiar datos
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación de almacén"""
    
    await update.message.reply_text(
        "❌ Operación cancelada.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Limpiar datos
    context.user_data.clear()
    return ConversationHandler.END

def register_almacen_handlers(application):
    """Registra los handlers para el módulo de almacén"""
    
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("almacen", almacen_command)],
        states={
            SELECCIONAR_ACCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_accion)],
            SELECCIONAR_FASE: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_fase)],
            INGRESAR_CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_cantidad)],
            CONFIRMAR_ACTUALIZACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_actualizacion)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador a la aplicación
    application.add_handler(conv_handler)
    logger.info("Handlers de almacén registrados")