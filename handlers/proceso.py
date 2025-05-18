import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler, ConversationHandler, MessageHandler, filters, 
    ContextTypes, CallbackQueryHandler
)
from config import PROCESO_FILE
from utils.db import append_data, get_all_data
from utils.sheets import update_cell, FASES_CAFE, TRANSICIONES_PERMITIDAS, es_transicion_valida, get_compras_por_fase
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
    keyboard = [[fase] for fase in FASES_CAFE]
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
    origen = update.message.text.strip().upper()
    
    # Verificar que la fase de origen sea válida
    if origen not in FASES_CAFE:
        keyboard = [[fase] for fase in FASES_CAFE]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "⚠️ Fase de origen no válida. Por favor, selecciona una de las opciones disponibles:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_ORIGEN
    
    # Guardar la fase de origen
    context.user_data['origen'] = origen
    logger.info(f"Usuario {update.effective_user.id} seleccionó fase de origen: {origen}")
    
    # Obtener compras disponibles en esa fase utilizando la nueva función
    compras_disponibles = get_compras_por_fase(origen)
    
    if not compras_disponibles:
        await update.message.reply_text(
            f"⚠️ No hay café disponible en fase {origen}.\n\n"
            "Por favor, registra una compra antes de procesar o selecciona otra fase de origen.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Calcular el total de kg disponibles
    total_kg = sum(safe_float(compra.get('kg_disponibles', 0)) for compra in compras_disponibles)
    
    # Guardar las compras disponibles para más tarde
    context.user_data['compras_disponibles'] = compras_disponibles
    context.user_data['total_kg_disponibles'] = total_kg
    
    # Obtener destinos posibles para esta fase
    if origen in TRANSICIONES_PERMITIDAS:
        destinos_posibles = TRANSICIONES_PERMITIDAS[origen]
        
        # Crear teclado con destinos posibles
        keyboard = [[destino] for destino in destinos_posibles]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"🔍 Hay {len(compras_disponibles)} compras de café en fase {origen} ({total_kg} kg disponibles)\n\n"
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

async def seleccionar_destino(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la fase de destino y mostrar las compras disponibles"""
    destino = update.message.text.strip().upper()
    origen = context.user_data['origen']
    
    # Verificar que la transición sea válida
    if not es_transicion_valida(origen, destino):
        # Crear teclado con destinos posibles
        destinos_posibles = TRANSICIONES_PERMITIDAS.get(origen, [])
        keyboard = [[destino] for destino in destinos_posibles]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"⚠️ Transición de {origen} a {destino} no válida. Por favor, selecciona un destino válido:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_DESTINO
    
    # Guardar la fase de destino
    context.user_data['destino'] = destino
    logger.info(f"Usuario {update.effective_user.id} seleccionó fase de destino: {destino}")
    
    # Mostrar las compras disponibles para selección
    compras_disponibles = context.user_data['compras_disponibles']
    
    # Inicializar lista para guardar las compras seleccionadas
    context.user_data['compras_seleccionadas'] = []
    
    # Crear teclado con las compras disponibles
    keyboard = []
    for i, compra in enumerate(compras_disponibles):
        fecha = compra.get('fecha', '')
        proveedor = compra.get('proveedor', '')
        kg_disponibles = safe_float(compra.get('kg_disponibles', 0))
        compra_id = compra.get('id', f"ID-{i}")  # Usar el ID único si existe, o generar uno temporal
        
        keyboard.append([
            InlineKeyboardButton(
                f"{fecha} - {proveedor} ({kg_disponibles} kg) [ID: {compra_id}]",
                callback_data=f"select_compra_{i}"
            )
        ])
    
    # Añadir botones para continuar o cancelar
    keyboard.append([
        InlineKeyboardButton("✅ Continuar con selección", callback_data="continue_selection"),
        InlineKeyboardButton("❌ Cancelar", callback_data="cancel_process")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🛒 SELECCIÓN DE COMPRAS A PROCESAR\n\n"
        f"Vas a transformar café de {origen} a {destino}.\n\n"
        f"Selecciona las compras que deseas procesar (puedes seleccionar varias):",
        reply_markup=reply_markup
    )
    return SELECCIONAR_COMPRAS

async def seleccionar_compras_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejar la selección de compras"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_process":
        await query.edit_message_text(
            "❌ Proceso cancelado.",
            reply_markup=None
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    if query.data == "continue_selection":
        # Verificar que haya al menos una compra seleccionada
        compras_seleccionadas = context.user_data.get('compras_seleccionadas', [])
        
        if not compras_seleccionadas:
            await query.edit_message_text(
                "⚠️ Debes seleccionar al menos una compra para continuar.\n\n"
                "Por favor, selecciona las compras a procesar:",
                reply_markup=query.message.reply_markup
            )
            return SELECCIONAR_COMPRAS
        
        # Calcular el total de kg disponibles en las compras seleccionadas
        total_kg_seleccionados = sum(safe_float(compra.get('kg_disponibles', 0)) for compra in compras_seleccionadas)
        
        # Guardar para uso posterior
        context.user_data['total_kg_seleccionados'] = total_kg_seleccionados
        
        # Mostrar resumen y solicitar la cantidad a procesar
        await query.edit_message_text(
            f"📋 RESUMEN DE SELECCIÓN\n\n"
            f"Has seleccionado {len(compras_seleccionadas)} compras con un total de {total_kg_seleccionados} kg disponibles.\n\n"
            f"A continuación, indica la cantidad a procesar."
        )
        
        await update.effective_chat.send_message(
            "✏️ Ingresa la cantidad de café a procesar (en kg):"
        )
        return INGRESAR_CANTIDAD
    
    # Si llegamos aquí, es una selección de compra
    if query.data.startswith("select_compra_"):
        index = int(query.data.replace("select_compra_", ""))
        compras_disponibles = context.user_data['compras_disponibles']
        
        if 0 <= index < len(compras_disponibles):
            compra = compras_disponibles[index]
            
            # Verificar si ya está seleccionada
            compras_seleccionadas = context.user_data.get('compras_seleccionadas', [])
            
            if compra in compras_seleccionadas:
                # Desmarcar
                compras_seleccionadas.remove(compra)
                logger.info(f"Usuario {update.effective_user.id} deseleccionó compra: {compra.get('proveedor')} [ID: {compra.get('id', 'N/A')}]")
            else:
                # Marcar
                compras_seleccionadas.append(compra)
                logger.info(f"Usuario {update.effective_user.id} seleccionó compra: {compra.get('proveedor')} [ID: {compra.get('id', 'N/A')}]")
            
            # Actualizar lista en el contexto
            context.user_data['compras_seleccionadas'] = compras_seleccionadas
            
            # Actualizar teclado marcando las seleccionadas
            keyboard = []
            for i, compra in enumerate(compras_disponibles):
                fecha = compra.get('fecha', '')
                proveedor = compra.get('proveedor', '')
                kg_disponibles = safe_float(compra.get('kg_disponibles', 0))
                compra_id = compra.get('id', f"ID-{i}")  # Usar el ID único si existe
                
                # Marcar con un check si está seleccionada
                prefix = "✅ " if compra in compras_seleccionadas else ""
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{prefix}{fecha} - {proveedor} ({kg_disponibles} kg) [ID: {compra_id}]",
                        callback_data=f"select_compra_{i}"
                    )
                ])
            
            # Añadir botones para continuar o cancelar
            keyboard.append([
                InlineKeyboardButton("✅ Continuar con selección", callback_data="continue_selection"),
                InlineKeyboardButton("❌ Cancelar", callback_data="cancel_process")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Mostrar total seleccionado
            total_kg_seleccionados = sum(safe_float(compra.get('kg_disponibles', 0)) for compra in compras_seleccionadas)
            mensaje = (
                f"🛒 SELECCIÓN DE COMPRAS A PROCESAR\n\n"
                f"Vas a transformar café de {context.user_data['origen']} a {context.user_data['destino']}.\n\n"
                f"Seleccionadas: {len(compras_seleccionadas)} compras ({total_kg_seleccionados} kg)\n\n"
                f"Selecciona las compras que deseas procesar (puedes seleccionar varias):"
            )
            
            await query.edit_message_text(mensaje, reply_markup=reply_markup)
            return SELECCIONAR_COMPRAS
    
    # Fallback
    await query.edit_message_text(
        "⚠️ Opción no válida.",
        reply_markup=None
    )
    return ConversationHandler.END

async def ingresar_cantidad(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar la cantidad ingresada y calcular la merma"""
    try:
        cantidad = safe_float(update.message.text)
        
        # Verificar que la cantidad sea válida
        if cantidad <= 0:
            await update.message.reply_text(
                "⚠️ La cantidad debe ser mayor que cero. Por favor, intenta nuevamente:"
            )
            return INGRESAR_CANTIDAD
        
        total_kg_seleccionados = context.user_data['total_kg_seleccionados']
        
        # Verificar que la cantidad no exceda el total disponible
        if cantidad > total_kg_seleccionados:
            await update.message.reply_text(
                f"⚠️ La cantidad ({cantidad} kg) no puede ser mayor que el total disponible ({total_kg_seleccionados} kg).\n\n"
                "Por favor, ingresa una cantidad válida:"
            )
            return INGRESAR_CANTIDAD
        
        # Guardar la cantidad
        context.user_data['cantidad'] = cantidad
        
        # Calcular la merma (si el destino requiere menos café que el origen)
        origen = context.user_data['origen']
        destino = context.user_data['destino']
        
        # Calculamos un porcentaje de merma basado en la transformación
        # Estos porcentajes pueden ajustarse según las necesidades del negocio
        merma_porcentajes = {
            ("CEREZO", "MOTE"): 70,       # Al despulpar el cerezo, se pierde la cáscara (70%)
            ("CEREZO", "PERGAMINO"): 80,  # Al pasar de cerezo a pergamino se pierde más material (80%)
            ("MOTE", "PERGAMINO"): 30,    # Al pasar de mote a pergamino se pierde menos (30%)
            ("PERGAMINO", "VERDE"): 20,   # Al quitar el pergamino (20%)
            ("PERGAMINO", "TOSTADO"): 35, # Nueva transición: PERGAMINO -> TOSTADO (35% = 20% pergamino + 15% humedad)
            ("VERDE", "TOSTADO"): 15,     # Al tostar (15% de pérdida por humedad)
            ("TOSTADO", "MOLIDO"): 0      # Al moler no hay pérdida significativa
        }
        
        # Obtener el porcentaje de merma para esta transición
        porcentaje_merma = merma_porcentajes.get((origen, destino), 0)
        
        if porcentaje_merma > 0:
            # Calcular la merma en kg
            merma_kg = (cantidad * porcentaje_merma) / 100
            
            # Redondear a 2 decimales
            merma_kg = round(merma_kg, 2)
            
            # Guardar la merma calculada
            context.user_data['merma'] = merma_kg
            
            # Preguntar por confirmación de la merma
            await update.message.reply_text(
                f"📊 CÁLCULO DE MERMA\n\n"
                f"Para procesar {cantidad} kg de {origen} a {destino}, se estima una merma de {merma_kg} kg ({porcentaje_merma}%).\n\n"
                f"¿Es correcta esta merma? Si no, ingresa el valor correcto:"
            )
            return CONFIRMAR_MERMA
        else:
            # No hay merma, guardar como 0
            context.user_data['merma'] = 0
            
            # Pasar directamente a notas
            await update.message.reply_text(
                "📝 Opcionalmente, puedes agregar notas o detalles sobre este proceso:\n"
                "(Envía '-' si no deseas agregar notas)"
            )
            return AGREGAR_NOTAS
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para la cantidad."
        )
        return INGRESAR_CANTIDAD

async def confirmar_merma(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar o corregir la merma"""
    try:
        merma_text = update.message.text.strip()
        
        # Si es un guión, mantener la merma calculada
        if merma_text == '-':
            # Ya tenemos la merma guardada, pasar a notas
            pass
        else:
            # Intentar convertir a número
            merma = safe_float(merma_text)
            
            # Verificar que la merma sea válida
            if merma < 0:
                await update.message.reply_text(
                    "⚠️ La merma no puede ser negativa. Por favor, intenta nuevamente:"
                )
                return CONFIRMAR_MERMA
            
            # Guardar la nueva merma
            context.user_data['merma'] = merma
        
        # Pasar a notas
        await update.message.reply_text(
            "📝 Opcionalmente, puedes agregar notas o detalles sobre este proceso:\n"
            "(Envía '-' si no deseas agregar notas)"
        )
        return AGREGAR_NOTAS
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para la merma."
        )
        return CONFIRMAR_MERMA

async def agregar_notas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar las notas y mostrar resumen para confirmar"""
    if update.message.text.strip() == '-':
        context.user_data['notas'] = ''
    else:
        context.user_data['notas'] = update.message.text.strip()
    
    # Mostrar resumen para confirmar
    origen = context.user_data['origen']
    destino = context.user_data['destino']
    cantidad = context.user_data['cantidad']
    merma = context.user_data['merma']
    notas = context.user_data['notas'] or 'N/A'
    compras_seleccionadas = context.user_data['compras_seleccionadas']
    
    # Preparar mensaje de resumen
    mensaje = (
        "📋 RESUMEN DEL PROCESO\n\n"
        f"Origen: {origen}\n"
        f"Destino: {destino}\n"
        f"Cantidad: {cantidad} kg\n"
        f"Merma estimada: {merma} kg\n"
        f"Compras seleccionadas: {len(compras_seleccionadas)}\n"
        f"Notas: {notas}\n\n"
    )
    
    # Añadir detalles de las compras seleccionadas
    mensaje += "📋 COMPRAS SELECCIONADAS:\n"
    for i, compra in enumerate(compras_seleccionadas):
        fecha = compra.get('fecha', '')
        proveedor = compra.get('proveedor', '')
        kg_disponibles = safe_float(compra.get('kg_disponibles', 0))
        compra_id = compra.get('id', f"ID-{i}")
        
        mensaje += f"{i+1}. {fecha} - {proveedor} ({kg_disponibles} kg) [ID: {compra_id}]\n"
    
    # Añadir pregunta de confirmación
    mensaje += "\n¿Confirmas este proceso? (Sí/No)"
    
    # Crear teclado para confirmación
    keyboard = [["Sí", "No"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(mensaje, reply_markup=reply_markup)
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
            
            # Mostrar mensaje de éxito
            await update.message.reply_text(
                "✅ Proceso registrado correctamente.\n\n"
                f"Se ha transformado {cantidad} kg de café de {origen} a {destino}.",
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