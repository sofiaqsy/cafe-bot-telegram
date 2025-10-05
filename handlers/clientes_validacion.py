"""
Módulo para gestionar validación de clientes desde Telegram
Permite revisar clientes pendientes, ver detalles y cambiar estados
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
import logging
from datetime import datetime
import pytz
from config import SPREADSHEET_ID
from utils.sheets import get_sheet_service

# Configurar zona horaria de Perú
peru_tz = pytz.timezone('America/Lima')

# Estados de conversación
MENU_PRINCIPAL, VER_CLIENTE, CAMBIAR_ESTADO_CLIENTE, FILTRAR_CLIENTES = range(4)

# Estados disponibles para clientes
ESTADOS_CLIENTE = {
    'Pendiente': '🟡 Pendiente de validación',
    'Verificado': '✅ Cliente verificado',
    'Rechazado': '❌ Cliente rechazado',
    'Prospecto': '🔍 Cliente prospecto'
}

# Configuración de logging
logger = logging.getLogger(__name__)

def obtener_clientes(filtro_estado=None):
    """
    Obtiene la lista de clientes de Google Sheets
    
    Args:
        filtro_estado: Si se proporciona, filtra por ese estado
    """
    try:
        service = get_sheet_service()
        if not service:
            logger.error("No se pudo obtener el servicio de Google Sheets")
            return []
        
        # Obtener datos de la hoja Clientes
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Clientes!A:Q'  # Hasta columna Q para incluir todos los campos
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            return []
        
        headers = values[0]
        clientes_data = []
        
        for row in values[1:]:
            # Asegurar que la fila tenga suficientes columnas
            while len(row) < len(headers):
                row.append('')
            
            cliente = {
                'id': row[0] if len(row) > 0 else '',
                'whatsapp': row[1] if len(row) > 1 else '',
                'empresa': row[2] if len(row) > 2 else '',
                'contacto': row[3] if len(row) > 3 else '',
                'telefono': row[4] if len(row) > 4 else '',
                'email': row[5] if len(row) > 5 else '',
                'direccion': row[6] if len(row) > 6 else '',
                'distrito': row[7] if len(row) > 7 else '',
                'ciudad': row[8] if len(row) > 8 else '',
                'fecha_registro': row[9] if len(row) > 9 else '',
                'ultima_compra': row[10] if len(row) > 10 else '',
                'total_pedidos': row[11] if len(row) > 11 else '0',
                'total_comprado': row[12] if len(row) > 12 else '0',
                'total_kg': row[13] if len(row) > 13 else '0',
                'notas': row[14] if len(row) > 14 else '',
                'estado': row[15] if len(row) > 15 else 'Pendiente',
                'imagen_url': row[16] if len(row) > 16 else ''  # URL de imagen de la cafetería
            }
            
            # Aplicar filtro si se especificó
            if filtro_estado:
                if cliente['estado'] == filtro_estado:
                    clientes_data.append(cliente)
            else:
                clientes_data.append(cliente)
        
        return clientes_data
        
    except Exception as e:
        logger.error(f"Error obteniendo clientes: {e}")
        return []

def actualizar_estado_cliente(cliente_id, nuevo_estado):
    """
    Actualiza el estado de un cliente en Google Sheets
    
    Args:
        cliente_id: ID del cliente
        nuevo_estado: Nuevo estado a asignar
    """
    try:
        service = get_sheet_service()
        if not service:
            return False
        
        # Primero obtener todos los clientes para encontrar la fila
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Clientes!A:Q'
        ).execute()
        
        values = result.get('values', [])
        
        # Encontrar la fila del cliente
        fila_cliente = None
        for i, row in enumerate(values):
            if len(row) > 0 and row[0] == cliente_id:
                fila_cliente = i + 1  # +1 porque Sheets empieza en 1
                break
        
        if not fila_cliente:
            logger.error(f"Cliente {cliente_id} no encontrado")
            return False
        
        # Actualizar el estado (columna P = 16)
        range_to_update = f'Clientes!P{fila_cliente}'
        
        body = {
            'values': [[nuevo_estado]]
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        logger.info(f"Cliente {cliente_id} actualizado a estado: {nuevo_estado}")
        return True
        
    except Exception as e:
        logger.error(f"Error actualizando estado del cliente: {e}")
        return False

async def clientes_validacion_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando principal para gestionar validación de clientes - Muestra pendientes por defecto"""
    
    # Limpiar contexto
    context.user_data.clear()
    
    # Por defecto, mostrar clientes pendientes
    clientes = obtener_clientes(filtro_estado="Pendiente")
    
    if not clientes:
        # Si no hay pendientes, mostrar el menú de filtros
        mensaje = "*🔍 VALIDACIÓN DE CLIENTES*\n"
        mensaje += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        mensaje += "⚠️ No hay clientes pendientes de validación\n\n"
        mensaje += "Selecciona qué clientes deseas ver:"
        
        keyboard = [
            [InlineKeyboardButton("✅ Clientes verificados", callback_data="cli_filter_Verificado")],
            [InlineKeyboardButton("❌ Clientes rechazados", callback_data="cli_filter_Rechazado")],
            [InlineKeyboardButton("🔍 Prospectos", callback_data="cli_filter_Prospecto")],
            [InlineKeyboardButton("📋 Ver todos", callback_data="cli_filter_todos")],
            [InlineKeyboardButton("❌ Salir", callback_data="cli_salir")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        return MENU_PRINCIPAL
    
    # Si hay clientes pendientes, mostrarlos directamente
    mensaje = "*🟡 CLIENTES PENDIENTES DE VALIDACIÓN*\n"
    mensaje += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    mensaje += f"Se encontraron {len(clientes)} cliente(s) pendiente(s)\n\n"
    mensaje += "Selecciona un cliente para validar:"
    
    keyboard = []
    for cliente in clientes[:15]:  # Máximo 15 clientes por página
        # Crear texto descriptivo del cliente
        empresa = cliente['empresa'] or 'Sin empresa'
        contacto = cliente['contacto'] or 'Sin contacto'
        
        texto_boton = f"🟡 {empresa[:20]} - {contacto[:15]}"
        
        keyboard.append([
            InlineKeyboardButton(
                texto_boton,
                callback_data=f"cli_ver_{cliente['id']}"
            )
        ])
    
    # Agregar botones de navegación
    keyboard.append([
        InlineKeyboardButton("🔄 Ver otros estados", callback_data="cli_menu_filtros")
    ])
    keyboard.append([InlineKeyboardButton("❌ Salir", callback_data="cli_salir")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.edit_message_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return VER_CLIENTE

async def filtrar_clientes_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el filtrado de clientes por estado"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.replace("cli_filter_", "")
    
    if data == "todos":
        clientes = obtener_clientes()
        titulo = "TODOS LOS CLIENTES"
    else:
        clientes = obtener_clientes(filtro_estado=data)
        titulo = f"CLIENTES - {ESTADOS_CLIENTE.get(data, data).upper()}"
    
    if not clientes:
        await query.edit_message_text(
            f"No hay clientes en estado: {data}\n\n"
            "Usa /clientes para volver al menú",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    # Mostrar lista de clientes
    mensaje = f"*{titulo}*\n"
    mensaje += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    mensaje += f"Se encontraron {len(clientes)} cliente(s)\n\n"
    mensaje += "Selecciona un cliente para ver detalles:"
    
    keyboard = []
    for cliente in clientes[:15]:  # Máximo 15 clientes por página
        # Crear texto descriptivo del cliente
        empresa = cliente['empresa'] or 'Sin empresa'
        contacto = cliente['contacto'] or 'Sin contacto'
        estado_emoji = '🟡' if cliente['estado'] == 'Pendiente' else '✅' if cliente['estado'] == 'Verificado' else '❌' if cliente['estado'] == 'Rechazado' else '🔍'
        
        texto_boton = f"{estado_emoji} {empresa[:20]} - {contacto[:15]}"
        
        keyboard.append([
            InlineKeyboardButton(
                texto_boton,
                callback_data=f"cli_ver_{cliente['id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="cli_volver")])
    keyboard.append([InlineKeyboardButton("❌ Salir", callback_data="cli_salir")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mensaje,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return VER_CLIENTE

async def ver_cliente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los detalles de un cliente específico"""
    query = update.callback_query
    await query.answer()
    
    # Manejar botón de ver otros estados
    if query.data == "cli_menu_filtros":
        # Mostrar menú de filtros
        mensaje = "*🔍 VALIDACIÓN DE CLIENTES*\n"
        mensaje += "━━━━━━━━━━━━━━━━━━━━━\n\n"
        mensaje += "Selecciona qué clientes deseas ver:"
        
        keyboard = [
            [InlineKeyboardButton("🟡 Pendientes de validación", callback_data="cli_filter_Pendiente")],
            [InlineKeyboardButton("✅ Clientes verificados", callback_data="cli_filter_Verificado")],
            [InlineKeyboardButton("❌ Clientes rechazados", callback_data="cli_filter_Rechazado")],
            [InlineKeyboardButton("🔍 Prospectos", callback_data="cli_filter_Prospecto")],
            [InlineKeyboardButton("📋 Ver todos", callback_data="cli_filter_todos")],
            [InlineKeyboardButton("❌ Salir", callback_data="cli_salir")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return MENU_PRINCIPAL
    
    if query.data == "cli_volver":
        return await clientes_validacion_command(update, context)
    
    if query.data == "cli_salir":
        await query.edit_message_text("✅ Gestión de clientes finalizada")
        return ConversationHandler.END
    
    # Obtener ID del cliente
    cliente_id = query.data.replace("cli_ver_", "")
    
    # Buscar el cliente
    clientes = obtener_clientes()
    cliente = None
    for c in clientes:
        if c['id'] == cliente_id:
            cliente = c
            break
    
    if not cliente:
        await query.edit_message_text("❌ Cliente no encontrado")
        return ConversationHandler.END
    
    # Guardar cliente en contexto para poder actualizarlo
    context.user_data['cliente_actual'] = cliente
    
    # Formatear mensaje con detalles del cliente
    mensaje = f"*📋 DETALLE DEL CLIENTE*\n"
    mensaje += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    mensaje += f"*ID:* `{cliente['id']}`\n"
    mensaje += f"*Estado:* {ESTADOS_CLIENTE.get(cliente['estado'], cliente['estado'])}\n\n"
    
    mensaje += "*📞 DATOS DE CONTACTO:*\n"
    mensaje += f"*Empresa:* {cliente['empresa'] or 'No especificada'}\n"
    mensaje += f"*Contacto:* {cliente['contacto'] or 'No especificado'}\n"
    mensaje += f"*WhatsApp:* {cliente['whatsapp'] or 'No especificado'}\n"
    mensaje += f"*Teléfono:* {cliente['telefono'] or 'No especificado'}\n"
    mensaje += f"*Email:* {cliente['email'] or 'No especificado'}\n\n"
    
    mensaje += "*📍 UBICACIÓN:*\n"
    mensaje += f"*Dirección:* {cliente['direccion'] or 'No especificada'}\n"
    mensaje += f"*Distrito:* {cliente['distrito'] or 'No especificado'}\n"
    mensaje += f"*Ciudad:* {cliente['ciudad'] or 'Lima'}\n\n"
    
    mensaje += "*📊 HISTORIAL:*\n"
    mensaje += f"*Fecha registro:* {cliente['fecha_registro'] or 'No especificada'}\n"
    mensaje += f"*Última compra:* {cliente['ultima_compra'] or 'Nunca'}\n"
    mensaje += f"*Total pedidos:* {cliente['total_pedidos']}\n"
    mensaje += f"*Total comprado:* S/{cliente['total_comprado']}\n"
    mensaje += f"*Total Kg:* {cliente['total_kg']} kg\n\n"
    
    if cliente.get('notas'):
        mensaje += f"*📝 Notas:* {cliente['notas']}\n\n"
    
    # Si hay imagen de la cafetería
    if cliente.get('imagen_url'):
        mensaje += f"*🏪 Imagen de la cafetería:*\n"
        mensaje += f"[Ver imagen]({cliente['imagen_url']})\n\n"
    
    mensaje += "━━━━━━━━━━━━━━━━━━━━━\n"
    mensaje += "¿Qué deseas hacer?"
    
    # Crear botones de acción
    keyboard = []
    
    # Botones para cambiar estado (solo mostrar estados diferentes al actual)
    estado_actual = cliente['estado']
    for estado_key, estado_desc in ESTADOS_CLIENTE.items():
        if estado_key != estado_actual:
            keyboard.append([
                InlineKeyboardButton(
                    f"Cambiar a: {estado_desc}",
                    callback_data=f"cli_estado_{estado_key}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("⬅️ Volver a lista", callback_data="cli_volver_lista")])
    keyboard.append([InlineKeyboardButton("❌ Salir", callback_data="cli_salir")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Si hay imagen, intentar enviarla primero
    if cliente.get('imagen_url'):
        try:
            # Intentar enviar la imagen con el caption
            await query.message.reply_photo(
                photo=cliente['imagen_url'],
                caption=mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            # Eliminar el mensaje anterior
            await query.message.delete()
        except Exception as e:
            logger.error(f"Error enviando imagen: {e}")
            # Si falla, enviar solo el texto
            await query.edit_message_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown',
                disable_web_page_preview=False
            )
    else:
        # Si no hay imagen, enviar solo texto
        await query.edit_message_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    return CAMBIAR_ESTADO_CLIENTE

async def cambiar_estado_cliente_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja el cambio de estado de un cliente"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cli_volver_lista":
        # Volver a la lista de clientes
        return await clientes_validacion_command(update, context)
    
    if query.data == "cli_salir":
        await query.edit_message_text("✅ Gestión de clientes finalizada")
        return ConversationHandler.END
    
    # Obtener el nuevo estado
    if query.data.startswith("cli_estado_"):
        nuevo_estado = query.data.replace("cli_estado_", "")
        cliente = context.user_data.get('cliente_actual')
        
        if not cliente:
            await query.edit_message_text("❌ Error: No se encontró el cliente en el contexto")
            return ConversationHandler.END
        
        # Actualizar estado en Google Sheets
        if actualizar_estado_cliente(cliente['id'], nuevo_estado):
            mensaje = f"✅ *ESTADO ACTUALIZADO*\n\n"
            mensaje += f"*Cliente:* {cliente['empresa'] or cliente['contacto']}\n"
            mensaje += f"*ID:* `{cliente['id']}`\n"
            mensaje += f"*Estado anterior:* {ESTADOS_CLIENTE.get(cliente['estado'], cliente['estado'])}\n"
            mensaje += f"*Estado nuevo:* {ESTADOS_CLIENTE.get(nuevo_estado, nuevo_estado)}\n\n"
            mensaje += "━━━━━━━━━━━━━━━━━━━━━\n"
            
            keyboard = [
                [InlineKeyboardButton("📋 Ver más clientes", callback_data="cli_volver_lista")],
                [InlineKeyboardButton("✅ Finalizar", callback_data="cli_salir")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Error actualizando el estado del cliente")
        
        return MENU_PRINCIPAL
    
    return ConversationHandler.END

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    await update.message.reply_text("❌ Gestión de clientes cancelada")
    return ConversationHandler.END

# Función para registrar los handlers
def register_clientes_handlers(app):
    """Registra los handlers de clientes en la aplicación"""
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("clientes", clientes_validacion_command),
            CommandHandler("validar_clientes", clientes_validacion_command)
        ],
        states={
            MENU_PRINCIPAL: [
                CallbackQueryHandler(filtrar_clientes_callback, pattern="^cli_filter_"),
                CallbackQueryHandler(cambiar_estado_cliente_callback, pattern="^cli_salir$")
            ],
            VER_CLIENTE: [
                CallbackQueryHandler(ver_cliente_callback, pattern="^cli_ver_"),
                CallbackQueryHandler(ver_cliente_callback, pattern="^cli_menu_filtros$"),
                CallbackQueryHandler(ver_cliente_callback, pattern="^cli_volver$"),
                CallbackQueryHandler(ver_cliente_callback, pattern="^cli_salir$")
            ],
            CAMBIAR_ESTADO_CLIENTE: [
                CallbackQueryHandler(cambiar_estado_cliente_callback, pattern="^cli_estado_"),
                CallbackQueryHandler(cambiar_estado_cliente_callback, pattern="^cli_volver_lista$"),
                CallbackQueryHandler(cambiar_estado_cliente_callback, pattern="^cli_salir$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command)
        ]
    )
    
    app.add_handler(conv_handler)
    logger.info("✅ Handlers de validación de clientes registrados")
