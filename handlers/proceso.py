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
    get_compras_por_fase, get_almacen_cantidad, actualizar_almacen_desde_proceso,
    leer_almacen_para_proceso, update_almacen, get_filtered_data
)
from utils.helpers import format_currency, get_now_peru, safe_float

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_ORIGEN, SELECCIONAR_DESTINO, SELECCIONAR_REGISTROS_ALMACEN, INGRESAR_CANTIDAD, CONFIRMAR_MERMA, AGREGAR_NOTAS, CONFIRMAR = range(7)

# Porcentajes aproximados de merma por tipo de transición
MERMAS_SUGERIDAS = {
    "CEREZO_MOTE": 0.85,      # 85% de pérdida de peso cerezo a mote
    "MOTE_PERGAMINO": 0.20,   # 20% de pérdida de mote a pergamino
    "PERGAMINO_VERDE": 0.18,  # 18% de pérdida de pergamino a verde
    "PERGAMINO_TOSTADO": 0.20, # 20% de pérdida de pergamino a tostado
    "PERGAMINO_MOLIDO": 0.25, # 25% de pérdida de pergamino a molido
    "VERDE_TOSTADO": 0.15,    # 15% de pérdida de verde a tostado
    "TOSTADO_MOLIDO": 0.05    # 5% de pérdida de tostado a molido
}

async def proceso_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de procesamiento"""
    logger.info(f"Usuario {update.effective_user.id} inició comando /proceso")
    
    # Limpiar datos previos
    context.user_data.clear()
    
    # Crear teclado solo con las fases que tienen kg disponibles
    keyboard = []
    
    # Leer datos del almacén para mostrar disponibilidad
    almacen_data = leer_almacen_para_proceso()
    
    # Mostrar solo las fases con cantidad disponible
    for fase in FASES_CAFE:
        # Obtener cantidad disponible en el almacén para esta fase
        cantidad_disponible = 0
        if fase in almacen_data:
            cantidad_disponible = almacen_data[fase]['cantidad_total']
        
        if cantidad_disponible > 0:
            keyboard.append([f"{fase} ({cantidad_disponible} kg)"])
    
    # Si no hay fases con café disponible, informar al usuario
    if not keyboard:
        await update.message.reply_text(
            "⚠️ No hay café disponible en el almacén para procesar.\n\n"
            "Por favor, registra compras primero antes de iniciar un proceso.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
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
                
        if not keyboard:
            await update.message.reply_text(
                "⚠️ No hay café disponible en el almacén para procesar.\n\n"
                "Por favor, registra compras primero antes de iniciar un proceso.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
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
    
    # Obtener destinos posibles para esta fase
    if origen in TRANSICIONES_PERMITIDAS:
        destinos_posibles = TRANSICIONES_PERMITIDAS[origen]
        
        # Si no hay destinos posibles, informar al usuario
        if not destinos_posibles:
            await update.message.reply_text(
                f"⚠️ La fase {origen} no tiene transformaciones posibles.\n"
                f"Por favor, inicia el proceso nuevamente con otra fase de origen.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        # Crear teclado con destinos posibles
        keyboard = [[destino] for destino in destinos_posibles]
        keyboard.append(["❌ Cancelar"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"🔍 Origen seleccionado: {origen}\n"
            f"📊 Almacén: {cantidad_almacen} kg disponibles\n\n"
            "Selecciona la fase de destino a la que quieres transformar el café:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_DESTINO
    else:
        await update.message.reply_text(
            f"⚠️ La fase {origen} no tiene transformaciones posibles.\n"
            f"Por favor, inicia el proceso nuevamente con otra fase de origen.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def seleccionar_destino(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la fase de destino y muestra los registros disponibles en el almacén"""
    destino = update.message.text.strip().upper()
    origen = context.user_data['origen']
    
    # Verificar si es cancelación
    if destino == "❌ CANCELAR":
        await update.message.reply_text(
            "❌ Operación cancelada.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Verificar que la fase de destino sea válida
    if not es_transicion_valida(origen, destino):
        # Mostrar error y regresar a selección de destino
        destinos_posibles = TRANSICIONES_PERMITIDAS.get(origen, [])
        keyboard = [[destino] for destino in destinos_posibles]
        keyboard.append(["❌ Cancelar"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"⚠️ Transición de {origen} a {destino} no es válida.\n\n"
            "Por favor, selecciona una de las opciones disponibles:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_DESTINO
    
    # Guardar la fase de destino
    context.user_data['destino'] = destino
    logger.info(f"Usuario {update.effective_user.id} seleccionó fase de destino: {destino}")
    
    # MEJORA: Obtener directamente los registros del almacén con la fase seleccionada
    almacen_registros = get_filtered_data('almacen', {'fase_actual': origen})
    
    # Filtrar solo los que tienen kg disponibles
    almacen_disponible = []
    for registro in almacen_registros:
        kg_disponibles = safe_float(registro.get('cantidad_actual', 0))
        if kg_disponibles > 0:
            almacen_disponible.append(registro)
    
    if not almacen_disponible:
        await update.message.reply_text(
            f"⚠️ No hay registros disponibles en el almacén para la fase {origen}.\n\n"
            "Por favor, inicia el proceso nuevamente con otra fase de origen.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Guardar los registros disponibles para más tarde
    context.user_data['almacen_disponible'] = almacen_disponible
    
    # Mostrar información de los registros disponibles y preguntar cuáles quiere procesar
    mensaje = f"🔍 Registros disponibles para procesar de fase {origen}:\n\n"
    
    # Crear teclado inline con los registros disponibles
    keyboard = []
    
    # Añadir botón para seleccionar todos los registros
    keyboard.append([
        InlineKeyboardButton("Seleccionar todos los registros", callback_data="todos")
    ])
    
    for i, registro in enumerate(almacen_disponible):
        # Extraer información del registro
        compra_id = registro.get('compra_id', 'Sin ID')
        kg_disponibles = safe_float(registro.get('cantidad_actual', 0))
        fecha = registro.get('fecha', 'Sin fecha')
        registro_id = registro.get('id', f"R{registro.get('_row_index', 'X')}")
        
        # Buscar información adicional si hay ID de compra
        proveedor = "Desconocido"
        if compra_id:
            compras = get_filtered_data('compras', {'id': compra_id})
            if compras:
                compra = compras[0]
                proveedor = compra.get('proveedor', 'Desconocido')
        
        # Extraer solo la fecha sin la hora
        fecha_solo = fecha.split(" ")[0] if " " in fecha else fecha
        
        # Añadir fila de información con el NUEVO formato: proveedor - id - kg - fecha
        mensaje += f"{i+1}. {proveedor} - {registro_id} - {kg_disponibles} kg - {fecha_solo}\n"
        
        # Crear botón para este registro con el NUEVO formato
        keyboard.append([
            InlineKeyboardButton(f"{proveedor} - {registro_id} - {kg_disponibles} kg - {fecha_solo}", callback_data=f"registro_{i}")
        ])
    
    # Añadir botón para selección múltiple personalizada
    keyboard.append([
        InlineKeyboardButton("Selección múltiple", callback_data="multi")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        mensaje + "\n¿Qué registros de almacén deseas procesar?",
        reply_markup=reply_markup
    )
    return SELECCIONAR_REGISTROS_ALMACEN

async def seleccionar_registros_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de registros de almacén a través de botones inline"""
    query = update.callback_query
    await query.answer()
    
    almacen_disponible = context.user_data['almacen_disponible']
    origen = context.user_data['origen']
    destino = context.user_data['destino']
    
    if query.data == "todos":
        # Seleccionar todos los registros
        context.user_data['registros_seleccionados'] = almacen_disponible
        # Calcular total de kg disponibles
        total_kg = sum(safe_float(registro.get('cantidad_actual', 0)) for registro in almacen_disponible)
        
        # Formatear mensaje con los registros seleccionados en el NUEVO formato
        seleccionados_info = []
        for registro in almacen_disponible:
            # Buscar información del proveedor
            proveedor = "Desconocido"
            compra_id = registro.get('compra_id', '')
            if compra_id:
                compras = get_filtered_data('compras', {'id': compra_id})
                if compras:
                    proveedor = compras[0].get('proveedor', 'Desconocido')
                    
            kg = safe_float(registro.get('cantidad_actual', 0))
            registro_id = registro.get('id', 'Sin ID')
            fecha = registro.get('fecha', 'Sin fecha')
            fecha_solo = fecha.split(" ")[0] if " " in fecha else fecha
            
            seleccionados_info.append(f"{proveedor} - {registro_id} - {kg} kg - {fecha_solo}")
        
        seleccionados_texto = "\n- ".join([""] + seleccionados_info)
        
        await query.edit_message_text(
            f"🛒 Has seleccionado todos los registros:{seleccionados_texto}\n\n"
            f"Total disponible: {total_kg} kg\n\n"
            f"¿Cuántos kg de café {origen} deseas transformar a {destino}?"
        )
        
        # Preguntar la cantidad a procesar
        await update.effective_chat.send_message(
            f"📝 Ingresa la cantidad en kg a procesar (máximo {total_kg} kg):",
            reply_markup=ReplyKeyboardRemove()
        )
        
        context.user_data['kg_disponibles'] = total_kg
        return INGRESAR_CANTIDAD
    
    elif query.data == "multi":
        # Implementar selección múltiple personalizada
        # Crear un nuevo teclado con checkboxes para selección múltiple
        keyboard = []
        for i, registro in enumerate(almacen_disponible):
            kg_disponibles = safe_float(registro.get('cantidad_actual', 0))
            registro_id = registro.get('id', 'Sin ID')
            
            # Buscar información del proveedor
            proveedor = "Desconocido"
            compra_id = registro.get('compra_id', '')
            if compra_id:
                compras = get_filtered_data('compras', {'id': compra_id})
                if compras:
                    proveedor = compras[0].get('proveedor', 'Desconocido')
            
            # Extraer fecha sin hora
            fecha = registro.get('fecha', 'Sin fecha')
            fecha_solo = fecha.split(" ")[0] if " " in fecha else fecha
            
            # Estado inicial: no seleccionado con el NUEVO formato
            checkbox = "☐"  # Checkbox vacío
            keyboard.append([
                InlineKeyboardButton(
                    f"{checkbox} {proveedor} - {registro_id} - {kg_disponibles} kg - {fecha_solo}", 
                    callback_data=f"toggle_{i}"
                )
            ])
        
        # Añadir botón para confirmar selección
        keyboard.append([
            InlineKeyboardButton("✅ Confirmar selección", callback_data="confirmar_multi")
        ])
        
        # Inicializar estructura para guardar selecciones
        context.user_data['multi_seleccion'] = {}
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📋 Selecciona múltiples registros (puedes marcar/desmarcar):",
            reply_markup=reply_markup
        )
        return SELECCIONAR_REGISTROS_ALMACEN
    
    elif query.data.startswith("toggle_"):
        # Actualizar estado de selección (toggle)
        indice = int(query.data.split("_")[1])
        multi_seleccion = context.user_data.get('multi_seleccion', {})
        
        # Toggle selection state
        if str(indice) in multi_seleccion:
            del multi_seleccion[str(indice)]
        else:
            multi_seleccion[str(indice)] = True
        
        # Save selection state
        context.user_data['multi_seleccion'] = multi_seleccion
        
        # Recreate keyboard with updated checkbox states
        keyboard = []
        for i, registro in enumerate(almacen_disponible):
            kg_disponibles = safe_float(registro.get('cantidad_actual', 0))
            registro_id = registro.get('id', 'Sin ID')
            
            # Buscar información del proveedor
            proveedor = "Desconocido"
            compra_id = registro.get('compra_id', '')
            if compra_id:
                compras = get_filtered_data('compras', {'id': compra_id})
                if compras:
                    proveedor = compras[0].get('proveedor', 'Desconocido')
            
            # Extraer fecha sin hora
            fecha = registro.get('fecha', 'Sin fecha')
            fecha_solo = fecha.split(" ")[0] if " " in fecha else fecha
            
            # Checkbox state based on selection
            checkbox = "☑" if str(i) in multi_seleccion else "☐"
            keyboard.append([
                InlineKeyboardButton(
                    f"{checkbox} {proveedor} - {registro_id} - {kg_disponibles} kg - {fecha_solo}", 
                    callback_data=f"toggle_{i}"
                )
            ])
        
        # Add confirmation button
        keyboard.append([
            InlineKeyboardButton("✅ Confirmar selección", callback_data="confirmar_multi")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📋 Selecciona múltiples registros (puedes marcar/desmarcar):",
            reply_markup=reply_markup
        )
        return SELECCIONAR_REGISTROS_ALMACEN
    
    elif query.data == "confirmar_multi":
        # Procesar selección múltiple confirmada
        multi_seleccion = context.user_data.get('multi_seleccion', {})
        
        if not multi_seleccion:
            # No hay selecciones, mostrar mensaje de error
            await query.edit_message_text(
                "⚠️ No has seleccionado ningún registro.\n\n"
                "Por favor, selecciona al menos un registro para procesar."
            )
            
            # Recrear el teclado original
            return await seleccionar_destino(update, context)
        
        # Crear lista de registros seleccionados
        registros_seleccionados = []
        for indice_str in multi_seleccion:
            indice = int(indice_str)
            if indice < len(almacen_disponible):
                registros_seleccionados.append(almacen_disponible[indice])
        
        context.user_data['registros_seleccionados'] = registros_seleccionados
        
        # Calcular total de kg disponibles
        total_kg = sum(safe_float(registro.get('cantidad_actual', 0)) for registro in registros_seleccionados)
        
        # Formatear mensaje con los registros seleccionados (NUEVO formato)
        seleccionados_info = []
        for registro in registros_seleccionados:
            # Buscar información del proveedor
            proveedor = "Desconocido"
            compra_id = registro.get('compra_id', '')
            if compra_id:
                compras = get_filtered_data('compras', {'id': compra_id})
                if compras:
                    proveedor = compras[0].get('proveedor', 'Desconocido')
                    
            kg = safe_float(registro.get('cantidad_actual', 0))
            registro_id = registro.get('id', 'Sin ID')
            fecha = registro.get('fecha', 'Sin fecha')
            fecha_solo = fecha.split(" ")[0] if " " in fecha else fecha
            
            seleccionados_info.append(f"{proveedor} - {registro_id} - {kg} kg - {fecha_solo}")
        
        seleccionados_texto = "\n- ".join([""] + seleccionados_info)
        
        await query.edit_message_text(
            f"🛒 Has seleccionado los siguientes registros:{seleccionados_texto}\n\n"
            f"Total disponible: {total_kg} kg\n\n"
            f"¿Cuántos kg de café {origen} deseas transformar a {destino}?"
        )
        
        # Preguntar la cantidad a procesar
        await update.effective_chat.send_message(
            f"📝 Ingresa la cantidad en kg a procesar (máximo {total_kg} kg):",
            reply_markup=ReplyKeyboardRemove()
        )
        
        context.user_data['kg_disponibles'] = total_kg
        return INGRESAR_CANTIDAD
    
    else:
        # Seleccionar un registro específico
        indice = int(query.data.split('_')[1])
        context.user_data['registros_seleccionados'] = [almacen_disponible[indice]]
        total_kg = safe_float(almacen_disponible[indice].get('cantidad_actual', 0))
        
        # Formatear mensaje con el NUEVO formato
        registro = almacen_disponible[indice]
        kg = safe_float(registro.get('cantidad_actual', 0))
        registro_id = registro.get('id', 'Sin ID')
        
        # Buscar información del proveedor
        proveedor = "Desconocido"
        compra_id = registro.get('compra_id', '')
        if compra_id:
            compras = get_filtered_data('compras', {'id': compra_id})
            if compras:
                proveedor = compras[0].get('proveedor', 'Desconocido')
        
        # Extraer fecha sin hora
        fecha = registro.get('fecha', 'Sin fecha')
        fecha_solo = fecha.split(" ")[0] if " " in fecha else fecha
        
        await query.edit_message_text(
            f"🛒 Has seleccionado el registro:\n- {proveedor} - {registro_id} - {kg} kg - {fecha_solo}\n\n"
            f"Total disponible: {total_kg} kg\n\n"
            f"¿Cuántos kg de café {origen} deseas transformar a {destino}?"
        )
        
        # Preguntar la cantidad a procesar
        await update.effective_chat.send_message(
            f"📝 Ingresa la cantidad en kg a procesar (máximo {total_kg} kg):",
            reply_markup=ReplyKeyboardRemove()
        )
        
        context.user_data['kg_disponibles'] = total_kg
        return INGRESAR_CANTIDAD

async def ingresar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la cantidad ingresada y solicita la cantidad de kilos resultantes"""
    # Obtener la cantidad ingresada
    try:
        texto_cantidad = update.message.text.strip().replace(',', '.')
        cantidad = float(texto_cantidad)
    except ValueError:
        await update.message.reply_text(
            "⚠️ La cantidad ingresada no es válida. Por favor, ingresa un número."
        )
        return INGRESAR_CANTIDAD
    
    # Verificar que la cantidad sea positiva
    if cantidad <= 0:
        await update.message.reply_text(
            "⚠️ La cantidad debe ser mayor que 0. Por favor, ingresa un valor válido."
        )
        return INGRESAR_CANTIDAD
    
    # Verificar que no exceda la cantidad disponible
    kg_disponibles = context.user_data['kg_disponibles']
    if cantidad > kg_disponibles:
        await update.message.reply_text(
            f"⚠️ La cantidad ingresada ({cantidad} kg) excede la cantidad disponible ({kg_disponibles} kg).\n"
            "Por favor, ingresa una cantidad menor o igual a la disponible."
        )
        return INGRESAR_CANTIDAD
    
    # Guardar la cantidad
    context.user_data['cantidad'] = cantidad
    logger.info(f"Usuario {update.effective_user.id} ingresó cantidad: {cantidad} kg")
    
    # Calcular merma sugerida según la transición
    origen = context.user_data['origen']
    destino = context.user_data['destino']
    
    transicion = f"{origen}_{destino}"
    merma_sugerida = round(cantidad * MERMAS_SUGERIDAS.get(transicion, 0.15), 2)  # Usar 15% como valor por defecto
    cantidad_resultante_esperada = cantidad - merma_sugerida
    
    # Guardar la merma sugerida y cantidad resultante esperada
    # El campo cantidad_resultante_esperada se guarda posteriormente en la base de datos
    context.user_data['merma_sugerida'] = merma_sugerida
    context.user_data['cantidad_resultante_esperada'] = cantidad_resultante_esperada
    
    # Solicitar la cantidad de kilos resultantes en lugar de la merma
    await update.message.reply_text(
        f"⚖️ ESTIMACIÓN DE CANTIDAD RESULTANTE\n\n"
        f"Transformar {cantidad} kg de {origen} a {destino} generaría aproximadamente {cantidad_resultante_esperada} kg de café.\n\n"
        f"Por favor, ingresa la cantidad de kilos resultante real:"
    )
    
    return CONFIRMAR_MERMA

async def confirmar_merma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma la cantidad de kilos resultante y calcula la merma"""
    texto_cantidad_resultante = update.message.text.strip()
    
    # Intentar convertir a número
    try:
        cantidad_resultante = float(texto_cantidad_resultante.replace(',', '.'))
        # Verificar que la cantidad resultante sea no negativa y no mayor que la cantidad
        cantidad = context.user_data['cantidad']
        if cantidad_resultante < 0:
            await update.message.reply_text(
                "⚠️ La cantidad resultante no puede ser negativa. Usando 0 como cantidad resultante."
            )
            cantidad_resultante = 0
        elif cantidad_resultante > cantidad:
            await update.message.reply_text(
                f"⚠️ La cantidad resultante ({cantidad_resultante} kg) no puede ser mayor que la cantidad a procesar ({cantidad} kg).\n"
                f"Usando la cantidad a procesar ({cantidad} kg) como cantidad resultante."
            )
            cantidad_resultante = cantidad
    except ValueError:
        await update.message.reply_text(
            f"⚠️ Valor de cantidad resultante no válido. Usando la cantidad resultante esperada de {context.user_data['cantidad_resultante_esperada']} kg."
        )
        cantidad_resultante = context.user_data['cantidad_resultante_esperada']
    
    # Guardar la cantidad resultante y calcular la merma real
    context.user_data['cantidad_resultante'] = cantidad_resultante
    cantidad = context.user_data['cantidad']
    merma = cantidad - cantidad_resultante
    context.user_data['merma'] = merma
    
    logger.info(f"Usuario {update.effective_user.id} ingresó cantidad resultante: {cantidad_resultante} kg, merma calculada: {merma} kg")
    
    # Solicitar notas adicionales
    await update.message.reply_text(
        "📝 Por favor, ingresa notas adicionales para este proceso (opcional):"
    )
    
    return AGREGAR_NOTAS

async def agregar_notas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar las notas y mostrar resumen para confirmación final"""
    notas = update.message.text.strip()
    
    # Guardar las notas
    context.user_data['notas'] = notas
    logger.info(f"Usuario {update.effective_user.id} ingresó notas: {notas}")
    
    # Obtener datos para resumen
    origen = context.user_data['origen']
    destino = context.user_data['destino']
    cantidad = context.user_data['cantidad']
    merma = context.user_data['merma']
    merma_sugerida = context.user_data['merma_sugerida']
    cantidad_resultante = context.user_data['cantidad_resultante']
    cantidad_resultante_esperada = context.user_data['cantidad_resultante_esperada']
    registros_seleccionados = context.user_data['registros_seleccionados']
    
    # Formatear información de registros con el NUEVO formato
    registros_info = []
    for registro in registros_seleccionados:
        # Obtener información del proveedor
        proveedor = "Desconocido"
        compra_id = registro.get('compra_id', '')
        if compra_id:
            compras = get_filtered_data('compras', {'id': compra_id})
            if compras:
                proveedor = compras[0].get('proveedor', 'Desconocido')
        
        kg = safe_float(registro.get('cantidad_actual', 0))
        registro_id = registro.get('id', 'Sin ID')
        fecha = registro.get('fecha', 'Sin fecha')
        fecha_solo = fecha.split(" ")[0] if " " in fecha else fecha
        
        registros_info.append(f"{proveedor} - {registro_id} - {kg} kg - {fecha_solo}")
    
    registros_texto = "\n- ".join([""] + registros_info)
    
    # Crear resumen
    resumen = (
        "📋 RESUMEN DEL PROCESO\n\n"
        f"Origen: {origen}\n"
        f"Destino: {destino}\n"
        f"Cantidad: {cantidad} kg\n"
        f"Merma estimada: {merma_sugerida} kg\n"
        f"Merma real: {merma} kg\n"
        f"Cantidad resultante esperada: {cantidad_resultante_esperada} kg\n"
        f"Cantidad resultante: {cantidad_resultante} kg\n"
        f"Registros:{registros_texto}\n\n"
        f"Notas: {notas or 'Sin notas adicionales'}\n\n"
        "¿Confirmas este proceso? (sí/no)"
    )
    
    # Crear teclado de confirmación
    keyboard = [["sí", "no"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        resumen,
        reply_markup=reply_markup
    )
    
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y guarda el proceso"""
    respuesta = update.message.text.lower()
    
    if respuesta in ["sí", "si", "s", "yes", "y"]:
        # Preparar datos para guardar
        origen = context.user_data['origen']
        destino = context.user_data['destino']
        cantidad = context.user_data['cantidad']
        merma = context.user_data['merma']
        merma_sugerida = context.user_data['merma_sugerida']
        cantidad_resultante = context.user_data['cantidad_resultante']
        cantidad_resultante_esperada = context.user_data['cantidad_resultante_esperada']
        notas = context.user_data['notas']
        registros_seleccionados = context.user_data['registros_seleccionados']
        
        # Obtener identificadores únicos de los registros seleccionados
        registros_ids = []
        compras_ids = []
        for registro in registros_seleccionados:
            # Usar el ID único del registro
            registro_id = registro.get('id', '')
            if registro_id:
                registros_ids.append(registro_id)
            
            # Añadir también el ID de compra si existe
            compra_id = registro.get('compra_id', '')
            if compra_id and compra_id not in compras_ids:
                compras_ids.append(compra_id)
        
        # Convertir a cadena
        registros_ids_str = ",".join(registros_ids)
        compras_ids_str = ",".join(compras_ids)
        
        # Obtener fecha y hora actual
        now = get_now_peru()
        
        # Datos para el proceso (actualizados con nuevos campos)
        # El campo cantidad_resultante_esperada se incluye aquí y se guarda en la base de datos
        proceso_data = {
            "fecha": now.strftime("%Y-%m-%d %H:%M:%S"),
            "origen": origen,
            "destino": destino,
            "cantidad": cantidad,
            "compras_ids": compras_ids_str,  # IDs de compras relacionadas
            "merma": merma,
            "merma_estimada": merma_sugerida,
            "cantidad_resultante_esperada": cantidad_resultante_esperada,  # Este campo ya se guarda correctamente
            "cantidad_resultante": cantidad_resultante,
            "notas": notas,
            "registrado_por": update.effective_user.username or update.effective_user.first_name
        }
        
        try:
            # 1. Guardar el proceso
            append_data("proceso", proceso_data)
            logger.info(f"Proceso guardado: {origen} -> {destino}, {cantidad} kg")
            
            # 2. Actualizar los registros del almacén procesados
            cantidad_restante = cantidad
            
            for registro in registros_seleccionados:
                row_index = registro.get('_row_index')
                kg_disponibles = safe_float(registro.get('cantidad_actual', 0))
                registro_id = registro.get('id', '')
                
                if cantidad_restante <= 0:
                    break
                
                # Determinar cuánto se procesa de este registro
                if cantidad_restante >= kg_disponibles:
                    # Se procesa todo el registro
                    cantidad_procesada = kg_disponibles
                    cantidad_restante -= kg_disponibles
                    nuevo_kg_disponibles = 0
                else:
                    # Se procesa parcialmente
                    cantidad_procesada = cantidad_restante
                    nuevo_kg_disponibles = kg_disponibles - cantidad_procesada
                    cantidad_restante = 0
                
                # Actualizar kg_disponibles en el registro de almacén
                update_cell("almacen", row_index, "cantidad_actual", nuevo_kg_disponibles)
                
                logger.info(f"Actualizado registro de almacén {registro_id} (fila {row_index}), nuevo cantidad_actual: {nuevo_kg_disponibles}")
            
            # 3. Crear nuevo registro en el almacén para la fase de destino
            if cantidad_resultante > 0:
                # Notas para el nuevo registro
                notas_destino = f"Procesado desde {origen}. IDs origen: {registros_ids_str}"
                
                # Crear nuevo registro en destino
                result_destino = update_almacen(
                    fase=destino,
                    cantidad_cambio=cantidad_resultante,
                    operacion="sumar",
                    notas=notas_destino,
                    compra_id=compras_ids_str if compras_ids_str else ""
                )
                
                # Manejar el caso en que result_destino es una tupla (desde actualizaciones recientes)
                if isinstance(result_destino, tuple):
                    resultado, almacen_id = result_destino
                    if resultado:
                        logger.info(f"Creado nuevo registro en almacén para fase {destino}: {cantidad_resultante} kg, ID: {almacen_id}")
                    else:
                        logger.warning(f"Error al crear registro en almacén para fase {destino}")
                else:
                    if result_destino:
                        logger.info(f"Creado nuevo registro en almacén para fase {destino}: {cantidad_resultante} kg")
                    else:
                        logger.warning(f"Error al crear registro en almacén para fase {destino}")
            
            # 4. Mostrar mensaje de éxito
            # Obtener cantidades actualizadas para mostrar
            nueva_cantidad_origen = get_almacen_cantidad(origen)
            nueva_cantidad_destino = get_almacen_cantidad(destino)
            
            await update.message.reply_text(
                "✅ Proceso registrado correctamente.\n\n"
                f"Se ha transformado {cantidad} kg de café de {origen} a {destino}.\n"
                f"Merma estimada: {merma_sugerida} kg\n"
                f"Merma real: {merma} kg\n"
                f"Cantidad resultante esperada: {cantidad_resultante_esperada} kg\n"
                f"Cantidad resultante: {cantidad_resultante} kg\n\n"
                f"📊 ALMACÉN ACTUALIZADO:\n"
                f"- {origen}: {nueva_cantidad_origen} kg disponibles\n"
                f"- {destino}: {nueva_cantidad_destino} kg disponibles",
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
            SELECCIONAR_REGISTROS_ALMACEN: [CallbackQueryHandler(seleccionar_registros_callback)],
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