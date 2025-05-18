import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler, ConversationHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler
)
from config import PROCESO_FILE
from utils.db import append_data, get_all_data
from utils.sheets import (
    update_cell, FASES_CAFE, TRANSICIONES_PERMITIDAS, es_transicion_valida, 
    get_compras_por_fase, get_almacen_cantidad, actualizar_almacen_desde_proceso
)
from utils.helpers import format_currency, get_now_peru, safe_float

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_ORIGEN, SELECCIONAR_DESTINO, SELECCIONAR_COMPRAS, INGRESAR_CANTIDAD, CONFIRMAR_MERMA, AGREGAR_NOTAS, CONFIRMAR = range(7)

# Headers para la hoja de proceso
PROCESO_HEADERS = ["fecha", "origen", "destino", "cantidad", "compras_ids", "merma", "notas", "registrado_por"]

async def proceso_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de procesamiento"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /proceso")
    
    # Limpiar datos previos
    context.user_data.clear()
    
    # Crear teclado con las fases disponibles como origen
    keyboard = []
    
    # Mostrar información de disponibilidad en el almacén para cada fase
    for fase in FASES_CAFE:
        # Obtener cantidad disponible en el almacén para esta fase
        cantidad_disponible = get_almacen_cantidad(fase)
        
        if cantidad_disponible > 0:
            keyboard.append([f"{fase} ({cantidad_disponible} kg)"])
        else:
            keyboard.append([fase])  # Sin mostrar cantidad si es 0
    
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "🔄 REGISTRO DE PROCESAMIENTO DE CAFÉ\n\n"
        "El procesamiento permite transformar el café de una fase a otra.\n\n"
        "Por favor, selecciona la fase de origen del café:",
        reply_markup=reply_markup
    )
    return SELECCIONAR_ORIGEN

async def seleccionar_origen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la fase de origen y solicitar la fase de destino"""
    # Extraer solo el nombre de la fase (eliminar la parte de la cantidad si existe)
    texto_origen = update.message.text.strip()
    origen = texto_origen.split(" (")[0].strip().upper()
    
    # Verificar que la fase de origen sea válida
    if origen not in FASES_CAFE:
        keyboard = []
        for fase in FASES_CAFE:
            cantidad_disponible = get_almacen_cantidad(fase)
            if cantidad_disponible > 0:
                keyboard.append([f"{fase} ({cantidad_disponible} kg)"])
            else:
                keyboard.append([fase])
                
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "⚠️ Fase de origen no válida. Por favor, selecciona una de las opciones disponibles:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_ORIGEN
    
    # Verificar disponibilidad en el almacén
    cantidad_almacen = get_almacen_cantidad(origen)
    if cantidad_almacen <= 0:
        await update.message.reply_text(
            f"⚠️ No hay café disponible en fase {origen} según el almacén central.\n\n"
            "Por favor, selecciona otra fase de origen o registra compras en esta fase primero.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Guardar la fase de origen
    context.user_data['origen'] = origen
    logger.info(f"Usuario {update.effective_user.id} seleccionó fase de origen: {origen} (disponible en almacén: {cantidad_almacen} kg)")
    
    # Obtener compras disponibles en esa fase utilizando la nueva función
    compras_disponibles = get_compras_por_fase(origen)
    
    # Mensajes de depuración para verificar las compras
    logger.info(f"Compras disponibles en fase {origen}: {len(compras_disponibles)}")
    for i, compra in enumerate(compras_disponibles):
        logger.info(f"Compra {i+1}: {compra.get('proveedor')} - {compra.get('kg_disponibles')} kg - ID: {compra.get('id')}")
    
    if not compras_disponibles:
        await update.message.reply_text(
            f"⚠️ No hay compras registradas en fase {origen}, aunque el almacén indica {cantidad_almacen} kg disponibles.\n\n"
            "Se recomienda sincronizar el almacén con las compras.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Calcular el total de kg disponibles
    total_kg = sum(safe_float(compra.get('kg_disponibles', 0)) for compra in compras_disponibles)
    
    # Verificar si hay diferencia entre almacén y compras
    if abs(total_kg - cantidad_almacen) > 0.1:  # Diferencia mayor a 0.1 kg
        logger.warning(f"Posible desincronización entre compras ({total_kg} kg) y almacén ({cantidad_almacen} kg) para fase {origen}")
    
    # Guardar las compras disponibles para más tarde
    context.user_data['compras_disponibles'] = compras_disponibles
    context.user_data['total_kg_disponibles'] = total_kg
    context.user_data['almacen_kg_disponibles'] = cantidad_almacen
    
    # Obtener destinos posibles para esta fase
    if origen in TRANSICIONES_PERMITIDAS:
        destinos_posibles = TRANSICIONES_PERMITIDAS[origen]
        
        # Crear teclado con destinos posibles
        keyboard = [[destino] for destino in destinos_posibles]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"🔍 Hay {len(compras_disponibles)} compras de café en fase {origen}.\n"
            f"📊 Almacén: {cantidad_almacen} kg disponibles\n\n"
            "Selecciona la fase de destino a la que quieres transformar el café:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_DESTINO
    else:
        await update.message.reply_text(
            f"⚠️ La fase {origen} no tiene transformaciones posibles."
            f"Por favor, inicia el proceso nuevamente con otra fase de origen.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

# El resto de las funciones se mantienen igual hasta la función confirmar

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda el proceso"""
    respuesta = update.message.text.lower()
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Preparar datos para guardar
        origen = context.user_data['origen']
        destino = context.user_data['destino']
        cantidad = context.user_data['cantidad']
        merma = context.user_data['merma']
        notas = context.user_data['notas']
        compras_seleccionadas = context.user_data['compras_seleccionadas']
        
        # Obtener identificadores únicos de las compras seleccionadas
        compras_ids = []
        for compra in compras_seleccionadas:
            # Usar el ID único si existe, si no, usar el índice de fila como fallback
            compra_id = compra.get('id', str(compra.get('_row_index', '')))
            compras_ids.append(compra_id)
        
        # Convertir a cadena
        compras_ids_str = ",".join(compras_ids)
        
        # Obtener fecha y hora actual
        now = get_now_peru()
        
        # Datos para el proceso
        proceso_data = {
            "fecha": now.strftime("%Y-%m-%d %H:%M:%S"),
            "origen": origen,
            "destino": destino,
            "cantidad": cantidad,
            "compras_ids": compras_ids_str,
            "merma": merma,
            "notas": notas,
            "registrado_por": update.effective_user.username or update.effective_user.first_name
        }
        
        try:
            # 1. Guardar el proceso
            append_data("proceso", proceso_data)
            
            # 2. Actualizar la fase_actual y kg_disponibles de las compras procesadas
            cantidad_restante = cantidad
            
            for compra in compras_seleccionadas:
                row_index = compra.get('_row_index')
                kg_disponibles = safe_float(compra.get('kg_disponibles', 0))
                
                if cantidad_restante <= 0:
                    break
                
                # Determinar cuánto se procesa de esta compra
                if cantidad_restante >= kg_disponibles:
                    # Se procesa toda la compra
                    cantidad_procesada = kg_disponibles
                    cantidad_restante -= kg_disponibles
                    nuevo_kg_disponibles = 0
                    
                    # Actualizar la fase_actual si se procesa toda la cantidad
                    update_cell("compras", row_index, "fase_actual", destino)
                    
                else:
                    # Se procesa parcialmente
                    cantidad_procesada = cantidad_restante
                    nuevo_kg_disponibles = kg_disponibles - cantidad_procesada
                    cantidad_restante = 0
                
                # Actualizar kg_disponibles
                update_cell("compras", row_index, "kg_disponibles", nuevo_kg_disponibles)
                
                logger.info(f"Actualizada compra {compra.get('id', 'N/A')} (fila {row_index}), nuevo kg_disponibles: {nuevo_kg_disponibles}")
            
            # 3. Actualizar el almacén central
            resultado_almacen = actualizar_almacen_desde_proceso(
                origen=origen,
                destino=destino,
                cantidad=cantidad,
                merma=merma
            )
            
            if resultado_almacen:
                logger.info(f"Almacén actualizado correctamente: {origen} -> {destino}, {cantidad} kg, merma: {merma} kg")
                
                # Obtener cantidades actualizadas para mostrar
                nueva_cantidad_origen = get_almacen_cantidad(origen)
                nueva_cantidad_destino = get_almacen_cantidad(destino)
                
                # Mostrar mensaje de éxito con info del almacén
                await update.message.reply_text(
                    "✅ Proceso registrado correctamente.\n\n"
                    f"Se ha transformado {cantidad} kg de café de {origen} a {destino}.\n\n"
                    f"📊 ALMACÉN ACTUALIZADO:\n"
                    f"- {origen}: {nueva_cantidad_origen} kg disponibles\n"
                    f"- {destino}: {nueva_cantidad_destino} kg disponibles",
                    reply_markup=ReplyKeyboardRemove()
                )
            else:
                logger.warning(f"El proceso se guardó correctamente, pero hubo un problema al actualizar el almacén")
                
                await update.message.reply_text(
                    "✅ Proceso registrado correctamente.\n\n"
                    f"Se ha transformado {cantidad} kg de café de {origen} a {destino}.\n\n"
                    "⚠️ Advertencia: Hubo un problema al actualizar el almacén central.",
                    reply_markup=ReplyKeyboardRemove()
                )
        except Exception as e:
            logger.error(f"Error al guardar proceso: {e}")
            await update.message.reply_text(
                "❌ Error al guardar el proceso. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await update.message.reply_text(
            "❌ Proceso cancelado.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Limpiar datos
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    await update.message.reply_text(
        "❌ Operación cancelada.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

def register_proceso_handlers(application):
    """Registra los handlers para el módulo de proceso"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("proceso", proceso_command)],
        states={
            SELECCIONAR_ORIGEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_origen)],
            SELECCIONAR_DESTINO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_destino)],
            SELECCIONAR_COMPRAS: [CallbackQueryHandler(seleccionar_compras_callback)],
            INGRESAR_CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, ingresar_cantidad)],
            CONFIRMAR_MERMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_merma)],
            AGREGAR_NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_notas)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador a la aplicación
    application.add_handler(conv_handler)
    logger.info("Handlers de proceso registrados")