"""
Módulo simplificado para gestionar pedidos de WhatsApp desde Telegram
Versión corregida - Compatible con la arquitectura de sheets del proyecto
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

# Configurar zona horaria de Perú
peru_tz = pytz.timezone('America/Lima')

# Estados de conversación
MENU_PRINCIPAL, BUSCAR_INPUT, VER_PEDIDO, CAMBIAR_ESTADO = range(4)

# Configuración de logging
logger = logging.getLogger(__name__)

# Estados disponibles para los pedidos
ESTADOS_PEDIDO = [
    "Pendiente verificación",
    "Pago verificado ✅", 
    "En preparación",
    "En camino",
    "Entregado",
    "Completado",
    "Cancelado"
]

# Emojis para estados
EMOJI_ESTADOS = {
    "Pendiente verificación": "⏳",
    "Pago verificado ✅": "✅",
    "En preparación": "👨‍🍳",
    "En camino": "🚚",
    "Entregado": "📦",
    "Completado": "✔️",
    "Cancelado": "❌"
}

def obtener_datos_pedidos():
    """Obtiene los pedidos de Google Sheets de forma síncrona"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            logger.error("No se pudo obtener el servicio de Google Sheets")
            return None
            
        # Obtener datos de la hoja PedidosWhatsApp
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='PedidosWhatsApp!A:T'
        ).execute()
        
        values = result.get('values', [])
        return values
        
    except Exception as e:
        logger.error(f"Error obteniendo pedidos: {e}")
        return None

def actualizar_estado_pedido(fila, columna, valor):
    """Actualiza una celda en Google Sheets de forma síncrona"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            return False
        
        # Convertir columna número a letra
        columna_letra = chr(64 + columna)  # 1=A, 2=B, etc.
        rango = f'PedidosWhatsApp!{columna_letra}{fila}'
        
        body = {'values': [[valor]]}
        
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=rango,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        
        return True
        
    except Exception as e:
        logger.error(f"Error actualizando estado: {e}")
        return False

async def pedidos_whatsapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando principal para gestionar pedidos de WhatsApp"""
    
    keyboard = [
        [InlineKeyboardButton("⏳ Ver pedidos pendientes", callback_data="pw_pendientes")],
        [InlineKeyboardButton("🔍 Buscar por ID", callback_data="pw_buscar_id")],
        [InlineKeyboardButton("📱 Buscar por teléfono", callback_data="pw_buscar_telefono")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="pw_cancelar")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensaje = """
🛒 *GESTIÓN DE PEDIDOS WHATSAPP*
━━━━━━━━━━━━━━━━━━━━━

Selecciona una opción:

• *Ver pendientes*: Pedidos sin verificar
• *Buscar por ID*: Buscar pedido específico
• *Buscar por teléfono*: Pedidos de un cliente

_Comando rápido: /pw_
"""
    
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

async def menu_principal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las opciones del menú principal"""
    query = update.callback_query
    await query.answer()
    
    opcion = query.data.replace("pw_", "")
    
    if opcion == "cancelar":
        await query.edit_message_text("❌ Operación cancelada")
        return ConversationHandler.END
    
    elif opcion == "pendientes":
        await query.edit_message_text("🔄 Cargando pedidos pendientes...")
        
        # Obtener pedidos
        pedidos = obtener_datos_pedidos()
        
        if not pedidos or len(pedidos) <= 1:
            await query.edit_message_text("📭 No hay pedidos registrados")
            return ConversationHandler.END
        
        # Filtrar solo pendientes
        pedidos_pendientes = []
        for i, pedido in enumerate(pedidos[1:], start=2):  # Skip header, start from row 2
            if len(pedido) > 14 and pedido[14] == "Pendiente verificación":
                pedidos_pendientes.append((i, pedido))
        
        if not pedidos_pendientes:
            keyboard = [[InlineKeyboardButton("🔙 Volver", callback_data="pw_volver_menu")]]
            await query.edit_message_text(
                "✅ No hay pedidos pendientes",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return MENU_PRINCIPAL
        
        # Mostrar lista de pendientes
        await mostrar_lista_pedidos(query, pedidos_pendientes, "PEDIDOS PENDIENTES")
        return VER_PEDIDO
    
    elif opcion == "buscar_id":
        await query.edit_message_text(
            "🔍 *BUSCAR POR ID*\n\n"
            "Envía el ID del pedido\n"
            "Ejemplo: `CAF-123456`\n\n"
            "_Escribe /cancelar para salir_",
            parse_mode='Markdown'
        )
        context.user_data['buscar_tipo'] = 'id'
        return BUSCAR_INPUT
    
    elif opcion == "buscar_telefono":
        await query.edit_message_text(
            "📱 *BUSCAR POR TELÉFONO*\n\n"
            "Envía el número de teléfono\n"
            "Ejemplo: `936934501`\n\n"
            "_Escribe /cancelar para salir_",
            parse_mode='Markdown'
        )
        context.user_data['buscar_tipo'] = 'telefono'
        return BUSCAR_INPUT

async def buscar_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la búsqueda por ID o teléfono"""
    texto = update.message.text.strip()
    tipo_busqueda = context.user_data.get('buscar_tipo')
    
    await update.message.reply_text("🔄 Buscando...")
    
    pedidos = obtener_datos_pedidos()
    if not pedidos or len(pedidos) <= 1:
        await update.message.reply_text("📭 No hay pedidos registrados")
        return ConversationHandler.END
    
    pedidos_encontrados = []
    
    if tipo_busqueda == 'id':
        # Normalizar ID
        texto = texto.upper()
        if not texto.startswith("CAF-"):
            texto = f"CAF-{texto}"
        
        # Buscar por ID
        for i, pedido in enumerate(pedidos[1:], start=2):
            if len(pedido) > 0 and pedido[0] == texto:
                pedidos_encontrados.append((i, pedido))
                break
    
    elif tipo_busqueda == 'telefono':
        # Normalizar teléfono
        texto = texto.replace("+51", "").replace(" ", "").replace("-", "")
        
        # Buscar por teléfono en columna T (índice 19)
        for i, pedido in enumerate(pedidos[1:], start=2):
            if len(pedido) > 19:
                telefono_pedido = str(pedido[19]).replace("+51", "").replace("'", "")
                if texto in telefono_pedido:
                    pedidos_encontrados.append((i, pedido))
    
    if not pedidos_encontrados:
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="pw_volver_menu")]]
        await update.message.reply_text(
            f"❌ No se encontraron pedidos\n\nBuscaste: *{texto}*\nTipo: {tipo_busqueda}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        return MENU_PRINCIPAL
    
    # Mostrar resultados
    titulo = f"BÚSQUEDA: {texto}"
    await mostrar_lista_pedidos(update, pedidos_encontrados, titulo)
    return VER_PEDIDO

async def mostrar_lista_pedidos(query_or_update, pedidos, titulo):
    """Muestra una lista de pedidos"""
    mensaje = f"""
📋 *{titulo}*
━━━━━━━━━━━━━━━━━━━━━
Total: *{len(pedidos)}* pedido(s)

"""
    
    keyboard = []
    
    for fila, pedido in pedidos[:10]:  # Máximo 10 pedidos
        try:
            id_pedido = pedido[0] if len(pedido) > 0 else "Sin ID"
            fecha = pedido[1] if len(pedido) > 1 else "-"
            empresa = pedido[3] if len(pedido) > 3 else "-"
            producto = pedido[7] if len(pedido) > 7 else "-"
            cantidad = pedido[8] if len(pedido) > 8 else "0"
            total = pedido[12] if len(pedido) > 12 else "0"
            estado = pedido[14] if len(pedido) > 14 else "Sin estado"
            emoji = EMOJI_ESTADOS.get(estado, "📋")
            
            # Truncar nombres largos
            if len(empresa) > 20:
                empresa = empresa[:20] + "..."
            if len(producto) > 25:
                producto = producto[:25] + "..."
            
            mensaje += f"{emoji} `{id_pedido}`\n"
            mensaje += f"📅 {fecha}\n"
            mensaje += f"🏢 {empresa}\n"
            mensaje += f"☕ {producto}\n"
            mensaje += f"📦 {cantidad}kg | 💰 S/{total}\n"
            mensaje += f"━━━━━━━━━━━━━━━\n"
            
            # Agregar botón para ver detalle
            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} {id_pedido}",
                    callback_data=f"ver_{fila}_{id_pedido}"
                )
            ])
            
        except Exception as e:
            logger.error(f"Error formateando pedido: {e}")
            continue
    
    if len(pedidos) > 10:
        mensaje += f"\n_⚠️ Mostrando 10 de {len(pedidos)} pedidos_"
    
    # Agregar botón de volver
    keyboard.append([
        InlineKeyboardButton("🔙 Volver al menú", callback_data="pw_volver_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Enviar mensaje
    if hasattr(query_or_update, 'edit_message_text'):
        await query_or_update.edit_message_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await query_or_update.message.reply_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def ver_detalle_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el detalle de un pedido específico"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "pw_volver_menu":
        return await pedidos_whatsapp_command(update, context)
    
    # Parsear datos del callback
    partes = query.data.split("_", 2)  # Dividir solo en 3 partes máximo
    if len(partes) < 3 or partes[0] != "ver":
        return VER_PEDIDO
    
    try:
        fila = int(partes[1])
        id_pedido = partes[2]  # El resto es el ID
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Error al procesar el pedido")
        return VER_PEDIDO
    
    # Guardar en contexto
    context.user_data['fila_actual'] = fila
    context.user_data['id_pedido_actual'] = id_pedido
    
    await query.edit_message_text("🔄 Cargando detalle...")
    
    # Obtener pedido actualizado
    pedidos = obtener_datos_pedidos()
    if not pedidos or len(pedidos) < fila:
        await query.edit_message_text("❌ Error al obtener el pedido")
        return ConversationHandler.END
    
    pedido = pedidos[fila - 1]
    
    # Formatear detalle
    mensaje = formatear_detalle_pedido(pedido)
    
    # Crear botones de estados
    keyboard = []
    estado_actual = pedido[14] if len(pedido) > 14 else ""
    
    # Organizar estados en filas de 2
    estados_disponibles = []
    for i, estado in enumerate(ESTADOS_PEDIDO):
        if estado != estado_actual:
            emoji = EMOJI_ESTADOS.get(estado, "📋")
            estados_disponibles.append(
                InlineKeyboardButton(
                    f"{emoji} {estado}",
                    callback_data=f"estado_{i}"
                )
            )
    
    # Agrupar de a 2
    for i in range(0, len(estados_disponibles), 2):
        if i + 1 < len(estados_disponibles):
            keyboard.append([estados_disponibles[i], estados_disponibles[i + 1]])
        else:
            keyboard.append([estados_disponibles[i]])
    
    # Botón de volver
    keyboard.append([
        InlineKeyboardButton("🔙 Volver", callback_data="pw_volver_menu")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        mensaje,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return CAMBIAR_ESTADO

def formatear_detalle_pedido(pedido):
    """Formatea el detalle de un pedido"""
    try:
        # Extraer campos con valores por defecto
        id_pedido = pedido[0] if len(pedido) > 0 else "N/A"
        fecha = pedido[1] if len(pedido) > 1 else "N/A"
        hora = pedido[2] if len(pedido) > 2 else "N/A"
        empresa = pedido[3] if len(pedido) > 3 else "N/A"
        contacto = pedido[4] if len(pedido) > 4 else "N/A"
        telefono = pedido[5] if len(pedido) > 5 else "N/A"
        direccion = pedido[6] if len(pedido) > 6 else "N/A"
        producto = pedido[7] if len(pedido) > 7 else "N/A"
        cantidad = pedido[8] if len(pedido) > 8 else "N/A"
        total = pedido[12] if len(pedido) > 12 else "N/A"
        metodo_pago = pedido[13] if len(pedido) > 13 else "N/A"
        estado = pedido[14] if len(pedido) > 14 else "N/A"
        whatsapp = pedido[19] if len(pedido) > 19 else "N/A"
        
        # Limpiar WhatsApp
        if whatsapp != "N/A":
            whatsapp = str(whatsapp).replace("'", "")
        
        emoji_estado = EMOJI_ESTADOS.get(estado, "📋")
        
        mensaje = f"""
{emoji_estado} *DETALLE DEL PEDIDO*
━━━━━━━━━━━━━━━━━━━━━

🆔 ID: `{id_pedido}`
📅 Fecha: {fecha}
🕐 Hora: {hora}

*DATOS DEL CLIENTE*
🏢 Empresa: {empresa}
👤 Contacto: {contacto}
📞 Teléfono: {telefono}
📱 WhatsApp: {whatsapp}
📍 Dirección: _{direccion}_

*INFORMACIÓN DEL PEDIDO*
☕ Producto: *{producto}*
📦 Cantidad: *{cantidad} kg*
💰 Total: *S/ {total}*
💳 Método: {metodo_pago}

*ESTADO ACTUAL*
{emoji_estado} *{estado}*

━━━━━━━━━━━━━━━━━━━━━
_Selecciona nuevo estado:_
"""
        
        return mensaje
        
    except Exception as e:
        logger.error(f"Error formateando detalle: {e}")
        return f"❌ Error al formatear pedido"

async def cambiar_estado_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cambia el estado de un pedido"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "pw_volver_menu":
        return await pedidos_whatsapp_command(update, context)
    
    if not query.data.startswith("estado_"):
        return CAMBIAR_ESTADO
    
    try:
        # Obtener nuevo estado
        estado_index = int(query.data.replace("estado_", ""))
        nuevo_estado = ESTADOS_PEDIDO[estado_index]
    except (ValueError, IndexError):
        await query.edit_message_text("❌ Error: Estado no válido")
        return CAMBIAR_ESTADO
    
    # Obtener datos guardados
    fila = context.user_data.get('fila_actual')
    id_pedido = context.user_data.get('id_pedido_actual')
    
    if not fila or not id_pedido:
        await query.edit_message_text("❌ Error: No se pudo identificar el pedido")
        return ConversationHandler.END
    
    await query.edit_message_text(f"🔄 Actualizando estado a: {nuevo_estado}...")
    
    # Actualizar estado (columna O = columna 15)
    exito = actualizar_estado_pedido(fila, 15, nuevo_estado)
    
    if exito:
        # Actualizar observaciones con timestamp
        ahora = datetime.now(peru_tz)
        timestamp = ahora.strftime("%d/%m %H:%M")
        usuario = update.effective_user.username or update.effective_user.first_name
        
        # Obtener observaciones actuales
        pedidos = obtener_datos_pedidos()
        obs_actuales = ""
        if pedidos and len(pedidos) >= fila and len(pedidos[fila - 1]) > 16:
            obs_actuales = pedidos[fila - 1][16] or ""
        
        # Nueva observación
        nueva_obs = f"[{timestamp}] {nuevo_estado} - @{usuario}"
        if obs_actuales:
            nueva_obs = f"{nueva_obs}\n{obs_actuales}"
        
        # Limitar longitud
        if len(nueva_obs) > 500:
            nueva_obs = nueva_obs[:497] + "..."
        
        # Actualizar observaciones (columna Q = columna 17)
        actualizar_estado_pedido(fila, 17, nueva_obs)
        
        emoji = EMOJI_ESTADOS.get(nuevo_estado, "✅")
        
        mensaje = f"""
{emoji} *ESTADO ACTUALIZADO*
━━━━━━━━━━━━━━━━━━━━━

📦 Pedido: `{id_pedido}`
📌 Nuevo estado: *{nuevo_estado}*
👤 Actualizado por: @{usuario}
🕐 Hora: {timestamp}

✅ _El cliente recibirá notificación por WhatsApp_
"""
        
        keyboard = [[
            InlineKeyboardButton("📋 Ver más pedidos", callback_data="pw_pendientes"),
            InlineKeyboardButton("🔙 Menú principal", callback_data="pw_volver_menu")
        ]]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MENU_PRINCIPAL
        
    else:
        await query.edit_message_text("❌ Error al actualizar el estado")
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual"""
    await update.message.reply_text("❌ Operación cancelada")
    return ConversationHandler.END

def register_pedidos_whatsapp_handlers(application):
    """Registra los handlers del módulo de pedidos WhatsApp"""
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('pedidos_whatsapp', pedidos_whatsapp_command),
            CommandHandler('pw', pedidos_whatsapp_command)  # Alias corto
        ],
        states={
            MENU_PRINCIPAL: [
                CallbackQueryHandler(menu_principal_callback, pattern='^pw_'),
                CallbackQueryHandler(pedidos_whatsapp_command, pattern='^pw_volver_menu$')
            ],
            BUSCAR_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_input),
                CallbackQueryHandler(pedidos_whatsapp_command, pattern='^pw_volver_menu$')
            ],
            VER_PEDIDO: [
                CallbackQueryHandler(ver_detalle_pedido, pattern='^ver_'),
                CallbackQueryHandler(pedidos_whatsapp_command, pattern='^pw_volver_menu$')
            ],
            CAMBIAR_ESTADO: [
                CallbackQueryHandler(cambiar_estado_callback, pattern='^estado_'),
                CallbackQueryHandler(pedidos_whatsapp_command, pattern='^pw_volver_menu$')
            ]
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar)
        ]
    )
    
    application.add_handler(conv_handler)
    logger.info("✅ Handlers de pedidos WhatsApp registrados correctamente")
