"""
Módulo para el comando /evidencias.
Este comando permite visualizar las últimas evidencias registradas.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from utils.sheets import get_all_data, get_filtered_data

# Configurar logging
logger = logging.getLogger(__name__)

# Cantidad máxima de evidencias a mostrar
MAX_EVIDENCIAS = 10

async def evidencias_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comando /evidencias para mostrar las últimas 10 evidencias registradas
    ordenadas por fecha (más reciente primero)
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /evidencias INICIADO por {username} (ID: {user_id}) ===")
    
    # Guardar contexto si hay algún filtro aplicado (por defecto, ninguno)
    if not hasattr(context, 'user_data') or 'evidencias_filtro' not in context.user_data:
        context.user_data['evidencias_filtro'] = None
    
    await mostrar_evidencias(update, context)

async def mostrar_evidencias(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_query=None):
    """
    Muestra las evidencias aplicando filtros si existen
    """
    filtro_tipo = context.user_data.get('evidencias_filtro')
    
    try:
        # Obtener todas las evidencias
        evidencias = get_all_data("documentos")
        
        if not evidencias:
            mensaje = "📂 *EVIDENCIAS REGISTRADAS*\n\n"
            mensaje += "No hay evidencias registradas en el sistema.\n\n"
            mensaje += "Utiliza el comando /evidencia para registrar una nueva evidencia."
            
            if callback_query:
                await callback_query.edit_message_text(mensaje, parse_mode="Markdown")
            else:
                await update.message.reply_text(mensaje, parse_mode="Markdown")
            return
        
        # Aplicar filtro si existe
        if filtro_tipo:
            evidencias_filtradas = [ev for ev in evidencias if ev.get('tipo_operacion') == filtro_tipo]
        else:
            evidencias_filtradas = evidencias
        
        # Ordenar por fecha descendente (más reciente primero)
        evidencias_ordenadas = sorted(evidencias_filtradas, key=lambda x: x.get('fecha', ''), reverse=True)
        
        # Limitar a las últimas evidencias
        evidencias_recientes = evidencias_ordenadas[:MAX_EVIDENCIAS]
        
        # Preparar mensaje
        if filtro_tipo:
            mensaje = f"📂 *EVIDENCIAS DE {filtro_tipo}*\n\n"
        else:
            mensaje = "📂 *ÚLTIMAS EVIDENCIAS REGISTRADAS*\n\n"
        
        # Añadir cada evidencia al mensaje
        for i, evidencia in enumerate(evidencias_recientes, 1):
            tipo_op = evidencia.get('tipo_operacion', 'N/A')
            op_id = evidencia.get('operacion_id', 'N/A')
            fecha = evidencia.get('fecha', 'Fecha desconocida')
            id_doc = evidencia.get('id', 'N/A')
            
            # Para gastos múltiples, mostrar número de gastos en lugar del ID
            if tipo_op == "GASTO" and "+" in op_id:
                num_gastos = len(op_id.split("+"))
                descripcion_op = f"{num_gastos} gastos agrupados"
            else:
                descripcion_op = f"ID: {op_id}"
            
            drive_link = ""
            if evidencia.get('drive_view_link'):
                drive_link = f" - [Ver en Drive]({evidencia.get('drive_view_link')})"
            
            mensaje += f"{i}. *{tipo_op}* - {descripcion_op}\n"
            mensaje += f"   📅 {fecha} - Doc: {id_doc}{drive_link}\n\n"
        
        # Añadir nota sobre el total de evidencias
        total_evidencias = len(evidencias_filtradas)
        if total_evidencias > MAX_EVIDENCIAS:
            mensaje += f"_Mostrando {MAX_EVIDENCIAS} de {total_evidencias} evidencias. Las evidencias se ordenan por fecha (más reciente primero)._\n\n"
        
        # Crear teclado con botones de filtro
        keyboard = [
            [
                InlineKeyboardButton("🔄 Todas", callback_data="evidencias_filtro_todas"),
                InlineKeyboardButton("🛒 Compras", callback_data="evidencias_filtro_COMPRA"),
                InlineKeyboardButton("💰 Ventas", callback_data="evidencias_filtro_VENTA")
            ],
            [
                InlineKeyboardButton("💸 Adelantos", callback_data="evidencias_filtro_ADELANTO"),
                InlineKeyboardButton("📊 Gastos", callback_data="evidencias_filtro_GASTO")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Responder al usuario con el mensaje y los botones
        if callback_query:
            await callback_query.edit_message_text(
                mensaje,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        else:
            await update.message.reply_text(
                mensaje,
                parse_mode="Markdown",
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        
    except Exception as e:
        logger.error(f"Error al listar evidencias: {e}")
        mensaje_error = "❌ Error al obtener las evidencias.\n\n"
        mensaje_error += "Por favor, intenta nuevamente más tarde o contacta al administrador."
        
        if callback_query:
            await callback_query.edit_message_text(mensaje_error, parse_mode="Markdown")
        else:
            await update.message.reply_text(mensaje_error, parse_mode="Markdown")

async def handle_evidencias_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja los callbacks de los botones de filtro de evidencias"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("evidencias_filtro_"):
        filtro = query.data.replace("evidencias_filtro_", "")
        
        # Actualizar el filtro actual
        if filtro == "todas":
            context.user_data['evidencias_filtro'] = None
        else:
            context.user_data['evidencias_filtro'] = filtro
        
        # Mostrar evidencias con el nuevo filtro
        await mostrar_evidencias(update, context, callback_query=query)

def register_evidencias_list_handlers(application):
    """Registra los handlers para el módulo de listado de evidencias"""
    try:
        # Registrar comando para listar evidencias
        application.add_handler(CommandHandler("evidencias", evidencias_command))
        
        # Registrar handler para los callbacks de filtro
        application.add_handler(CallbackQueryHandler(
            handle_evidencias_callback,
            pattern=r"^evidencias_filtro_"
        ))
        
        logger.info("Handler de listado de evidencias registrado")
        return True
    except Exception as e:
        logger.error(f"Error al registrar handler de listado de evidencias: {e}")
        return False