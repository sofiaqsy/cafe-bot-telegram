"""
Módulo para gestionar pedidos de WhatsApp desde Telegram
Permite visualizar, filtrar y actualizar estados de pedidos
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
from datetime import datetime, timedelta
import pytz

# Configurar zona horaria de Perú
peru_tz = pytz.timezone('America/Lima')

# Estados de conversación
SELECCIONAR_FILTRO, MOSTRAR_PEDIDOS, SELECCIONAR_PEDIDO, CAMBIAR_ESTADO = range(4)

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

async def pedidos_whatsapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando principal para gestionar pedidos de WhatsApp"""
    
    keyboard = [
        [
            InlineKeyboardButton("📋 Ver todos los pedidos", callback_data="pw_todos"),
            InlineKeyboardButton("⏳ Solo pendientes", callback_data="pw_pendientes")
        ],
        [
            InlineKeyboardButton("📅 Pedidos de hoy", callback_data="pw_hoy"),
            InlineKeyboardButton("📆 Últimos 7 días", callback_data="pw_semana")
        ],
        [
            InlineKeyboardButton("🔍 Buscar por ID", callback_data="pw_buscar_id"),
            InlineKeyboardButton("📱 Buscar por WhatsApp", callback_data="pw_buscar_wa")
        ],
        [
            InlineKeyboardButton("📊 Estadísticas", callback_data="pw_stats"),
            InlineKeyboardButton("❌ Cancelar", callback_data="pw_cancelar")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensaje = """
🛒 *GESTIÓN DE PEDIDOS WHATSAPP*
━━━━━━━━━━━━━━━━━━━━━

Selecciona una opción para gestionar los pedidos:

• *Ver todos*: Lista completa de pedidos
• *Solo pendientes*: Pedidos sin verificar
• *Pedidos de hoy*: Pedidos del día actual
• *Últimos 7 días*: Pedidos recientes
• *Buscar por ID*: Encuentra un pedido específico
• *Buscar por WhatsApp*: Pedidos de un cliente
• *Estadísticas*: Resumen general

¿Qué deseas hacer?
"""
    
    await update.message.reply_text(
        mensaje,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return SELECCIONAR_FILTRO

async def seleccionar_filtro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección del filtro para mostrar pedidos"""
    query = update.callback_query
    await query.answer()
    
    filtro = query.data.replace("pw_", "")
    context.user_data['filtro_pedidos'] = filtro
    
    if filtro == "cancelar":
        await query.edit_message_text("Operación cancelada.")
        return ConversationHandler.END
    
    if filtro == "buscar_id":
        await query.edit_message_text(
            "🔍 *Buscar pedido por ID*\n\n"
            "Envía el ID del pedido (ejemplo: CAF-123456):",
            parse_mode='Markdown'
        )
        return MOSTRAR_PEDIDOS
    
    if filtro == "buscar_wa":
        await query.edit_message_text(
            "📱 *Buscar pedidos por WhatsApp*\n\n"
            "Envía el número de WhatsApp del cliente\n"
            "(ejemplo: 936934501 o +51936934501):",
            parse_mode='Markdown'
        )
        return MOSTRAR_PEDIDOS
    
    if filtro == "stats":
        await mostrar_estadisticas(query, context)
        return ConversationHandler.END
    
    # Obtener y mostrar pedidos según el filtro
    await mostrar_pedidos(query, context, filtro)
    return SELECCIONAR_PEDIDO

async def mostrar_pedidos(query_or_update, context: ContextTypes.DEFAULT_TYPE, filtro: str):
    """Muestra los pedidos según el filtro seleccionado"""
    
    # Importar aquí para evitar importación circular
    from utils.sheets import get_sheet_service, get_all_data
    
    try:
        # Obtener servicio de Google Sheets
        service = await get_sheet_service()
        if not service:
            mensaje = "❌ Error: No se pudo conectar con Google Sheets"
            if hasattr(query_or_update, 'edit_message_text'):
                await query_or_update.edit_message_text(mensaje)
            else:
                await query_or_update.message.reply_text(mensaje)
            return
        
        # Leer datos de la hoja PedidosWhatsApp
        pedidos = await get_all_data("PedidosWhatsApp")
        
        if not pedidos or len(pedidos) <= 1:
            mensaje = "📭 No hay pedidos registrados"
            if hasattr(query_or_update, 'edit_message_text'):
                await query_or_update.edit_message_text(mensaje)
            else:
                await query_or_update.message.reply_text(mensaje)
            return
        
        # Filtrar pedidos según el criterio
        pedidos_filtrados = filtrar_pedidos(pedidos[1:], filtro, context)  # Skip header
        
        if not pedidos_filtrados:
            mensaje = f"📭 No se encontraron pedidos para el filtro: *{filtro}*"
            if hasattr(query_or_update, 'edit_message_text'):
                await query_or_update.edit_message_text(mensaje, parse_mode='Markdown')
            else:
                await query_or_update.message.reply_text(mensaje, parse_mode='Markdown')
            return
        
        # Crear mensaje con los pedidos
        mensaje = formatear_lista_pedidos(pedidos_filtrados, filtro)
        
        # Crear botones para cada pedido (máximo 10)
        keyboard = []
        for i, pedido in enumerate(pedidos_filtrados[:10]):
            id_pedido = pedido[0]  # Columna A: ID_Pedido
            estado = pedido[14] if len(pedido) > 14 else "Sin estado"  # Columna O
            emoji = EMOJI_ESTADOS.get(estado, "📋")
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{emoji} {id_pedido}", 
                    callback_data=f"ver_{id_pedido}"
                )
            ])
        
        # Agregar botón de volver
        keyboard.append([
            InlineKeyboardButton("🔙 Volver al menú", callback_data="pw_volver")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
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
            
    except Exception as e:
        logger.error(f"Error mostrando pedidos: {e}")
        mensaje = f"❌ Error al obtener pedidos: {str(e)}"
        if hasattr(query_or_update, 'edit_message_text'):
            await query_or_update.edit_message_text(mensaje)
        else:
            await query_or_update.message.reply_text(mensaje)

def filtrar_pedidos(pedidos, filtro, context):
    """Filtra los pedidos según el criterio seleccionado"""
    ahora = datetime.now(peru_tz)
    hoy = ahora.date()
    
    if filtro == "todos":
        return pedidos
    
    elif filtro == "pendientes":
        return [p for p in pedidos if len(p) > 14 and p[14] == "Pendiente verificación"]
    
    elif filtro == "hoy":
        pedidos_hoy = []
        for p in pedidos:
            try:
                if len(p) > 1 and p[1]:  # Columna B: Fecha
                    fecha_str = p[1]
                    # Parsear fecha en formato DD/MM/YYYY
                    fecha_pedido = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                    if fecha_pedido == hoy:
                        pedidos_hoy.append(p)
            except:
                continue
        return pedidos_hoy
    
    elif filtro == "semana":
        hace_7_dias = hoy - timedelta(days=7)
        pedidos_semana = []
        for p in pedidos:
            try:
                if len(p) > 1 and p[1]:  # Columna B: Fecha
                    fecha_str = p[1]
                    fecha_pedido = datetime.strptime(fecha_str, "%d/%m/%Y").date()
                    if hace_7_dias <= fecha_pedido <= hoy:
                        pedidos_semana.append(p)
            except:
                continue
        return pedidos_semana
    
    elif filtro.startswith("id_"):
        # Buscar por ID específico
        id_buscar = context.user_data.get('buscar_valor', '').upper()
        return [p for p in pedidos if len(p) > 0 and p[0] == id_buscar]
    
    elif filtro.startswith("wa_"):
        # Buscar por WhatsApp
        wa_buscar = context.user_data.get('buscar_valor', '').replace('+51', '')
        pedidos_wa = []
        for p in pedidos:
            if len(p) > 19 and p[19]:  # Columna T: Usuario_WhatsApp
                wa_pedido = p[19].replace('+51', '').replace("'", '')
                if wa_buscar in wa_pedido:
                    pedidos_wa.append(p)
        return pedidos_wa
    
    return pedidos

def formatear_lista_pedidos(pedidos, filtro):
    """Formatea la lista de pedidos para mostrar"""
    titulo = {
        "todos": "TODOS LOS PEDIDOS",
        "pendientes": "PEDIDOS PENDIENTES",
        "hoy": "PEDIDOS DE HOY",
        "semana": "ÚLTIMOS 7 DÍAS",
    }.get(filtro, "PEDIDOS FILTRADOS")
    
    mensaje = f"""
📋 *{titulo}*
━━━━━━━━━━━━━━━━━━━━━
Total: {len(pedidos)} pedidos

"""
    
    for i, pedido in enumerate(pedidos[:10]):  # Mostrar máximo 10
        try:
            id_pedido = pedido[0] if len(pedido) > 0 else "Sin ID"
            fecha = pedido[1] if len(pedido) > 1 else "Sin fecha"
            empresa = pedido[3] if len(pedido) > 3 else "Sin empresa"
            producto = pedido[7] if len(pedido) > 7 else "Sin producto"
            cantidad = pedido[8] if len(pedido) > 8 else "0"
            total = pedido[12] if len(pedido) > 12 else "0"
            estado = pedido[14] if len(pedido) > 14 else "Sin estado"
            emoji = EMOJI_ESTADOS.get(estado, "📋")
            
            mensaje += f"""
{emoji} *{id_pedido}*
📅 {fecha} | 🏢 {empresa}
☕ {producto} - {cantidad}kg
💰 S/ {total}
Estado: _{estado}_
━━━━━━━━━━━━━━━━
"""
        except Exception as e:
            logger.error(f"Error formateando pedido: {e}")
            continue
    
    if len(pedidos) > 10:
        mensaje += f"\n_Mostrando 10 de {len(pedidos)} pedidos_"
    
    mensaje += "\n*Selecciona un pedido para ver detalles:*"
    
    return mensaje

async def ver_detalle_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra el detalle de un pedido específico"""
    query = update.callback_query
    await query.answer()
    
    # Obtener ID del pedido
    id_pedido = query.data.replace("ver_", "")
    context.user_data['pedido_actual'] = id_pedido
    
    # Importar aquí para evitar importación circular
    from utils.sheets import get_sheet_service, get_all_data
    
    try:
        # Obtener datos del pedido
        pedidos = await get_all_data("PedidosWhatsApp")
        pedido = None
        fila_pedido = None
        
        for i, p in enumerate(pedidos[1:], start=2):  # Empezar desde fila 2
            if len(p) > 0 and p[0] == id_pedido:
                pedido = p
                fila_pedido = i
                break
        
        if not pedido:
            await query.edit_message_text(f"❌ No se encontró el pedido {id_pedido}")
            return ConversationHandler.END
        
        # Guardar fila para actualización posterior
        context.user_data['fila_pedido'] = fila_pedido
        
        # Formatear detalle del pedido
        mensaje = formatear_detalle_pedido(pedido)
        
        # Crear botones de estados
        keyboard = []
        estado_actual = pedido[14] if len(pedido) > 14 else ""
        
        # Mostrar solo estados diferentes al actual
        for estado in ESTADOS_PEDIDO:
            if estado != estado_actual:
                emoji = EMOJI_ESTADOS.get(estado, "📋")
                keyboard.append([
                    InlineKeyboardButton(
                        f"{emoji} Cambiar a: {estado}",
                        callback_data=f"estado_{ESTADOS_PEDIDO.index(estado)}"
                    )
                ])
        
        # Botones de acción
        keyboard.append([
            InlineKeyboardButton("📝 Agregar nota", callback_data="nota_pedido"),
            InlineKeyboardButton("🔄 Actualizar", callback_data=f"ver_{id_pedido}")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 Volver a lista", callback_data="pw_volver_lista")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CAMBIAR_ESTADO
        
    except Exception as e:
        logger.error(f"Error viendo detalle: {e}")
        await query.edit_message_text(f"❌ Error al obtener detalle: {str(e)}")
        return ConversationHandler.END

def formatear_detalle_pedido(pedido):
    """Formatea el detalle completo de un pedido"""
    try:
        # Extraer todos los campos (columnas A-T)
        id_pedido = pedido[0] if len(pedido) > 0 else "N/A"
        fecha = pedido[1] if len(pedido) > 1 else "N/A"
        hora = pedido[2] if len(pedido) > 2 else "N/A"
        empresa = pedido[3] if len(pedido) > 3 else "N/A"
        contacto = pedido[4] if len(pedido) > 4 else "N/A"
        telefono = pedido[5] if len(pedido) > 5 else "N/A"
        direccion = pedido[6] if len(pedido) > 6 else "N/A"
        producto = pedido[7] if len(pedido) > 7 else "N/A"
        cantidad = pedido[8] if len(pedido) > 8 else "N/A"
        precio_unit = pedido[9] if len(pedido) > 9 else "N/A"
        subtotal = pedido[10] if len(pedido) > 10 else "N/A"
        descuento = pedido[11] if len(pedido) > 11 else "N/A"
        total = pedido[12] if len(pedido) > 12 else "N/A"
        metodo_pago = pedido[13] if len(pedido) > 13 else "N/A"
        estado = pedido[14] if len(pedido) > 14 else "N/A"
        comprobante = pedido[15] if len(pedido) > 15 else "N/A"
        observaciones = pedido[16] if len(pedido) > 16 else "N/A"
        tipo = pedido[17] if len(pedido) > 17 else "N/A"
        id_cliente = pedido[18] if len(pedido) > 18 else "N/A"
        whatsapp = pedido[19] if len(pedido) > 19 else "N/A"
        
        # Formatear WhatsApp
        if whatsapp and whatsapp != "N/A":
            whatsapp = whatsapp.replace("'", "")
        
        # Calcular tiempo transcurrido
        tiempo_transcurrido = "N/A"
        try:
            if fecha != "N/A" and hora != "N/A":
                fecha_pedido = datetime.strptime(f"{fecha} {hora}", "%d/%m/%Y %H:%M:%S %p")
                ahora = datetime.now()
                diferencia = ahora - fecha_pedido
                
                if diferencia.days > 0:
                    tiempo_transcurrido = f"{diferencia.days} días"
                elif diferencia.seconds > 3600:
                    horas = diferencia.seconds // 3600
                    tiempo_transcurrido = f"{horas} horas"
                else:
                    minutos = diferencia.seconds // 60
                    tiempo_transcurrido = f"{minutos} minutos"
        except:
            pass
        
        emoji_estado = EMOJI_ESTADOS.get(estado, "📋")
        
        mensaje = f"""
{emoji_estado} *DETALLE DE PEDIDO*
━━━━━━━━━━━━━━━━━━━━━

🆔 *ID:* `{id_pedido}`
📅 *Fecha:* {fecha} {hora}
⏱️ *Tiempo transcurrido:* {tiempo_transcurrido}

👤 *DATOS DEL CLIENTE*
• *Empresa:* {empresa}
• *Contacto:* {contacto}
• *Teléfono:* {telefono}
• *WhatsApp:* {whatsapp}
• *Dirección:* {direccion}

☕ *DATOS DEL PEDIDO*
• *Producto:* {producto}
• *Cantidad:* {cantidad} kg
• *Precio Unit:* S/ {precio_unit}
• *Subtotal:* S/ {subtotal}
• *Descuento:* {descuento}%
• *Total:* S/ *{total}*

💳 *Método de pago:* {metodo_pago}
📸 *Comprobante:* {comprobante}

📌 *Estado actual:* *{estado}*
💬 *Observaciones:* {observaciones if observaciones != 'N/A' else 'Sin observaciones'}
🔄 *Tipo:* {tipo}

━━━━━━━━━━━━━━━━━━━━━
_Selecciona una acción:_
"""
        
        return mensaje
        
    except Exception as e:
        logger.error(f"Error formateando detalle: {e}")
        return f"❌ Error al formatear pedido: {str(e)}"

async def cambiar_estado_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cambia el estado de un pedido"""
    query = update.callback_query
    await query.answer()
    
    # Manejar botones especiales
    if query.data == "pw_volver_lista":
        filtro = context.user_data.get('filtro_pedidos', 'todos')
        await mostrar_pedidos(query, context, filtro)
        return SELECCIONAR_PEDIDO
    
    if query.data == "nota_pedido":
        await query.edit_message_text(
            "📝 *Agregar nota al pedido*\n\n"
            "Envía la nota que deseas agregar al pedido:",
            parse_mode='Markdown'
        )
        context.user_data['esperando_nota'] = True
        return CAMBIAR_ESTADO
    
    if query.data.startswith("ver_"):
        # Actualizar vista del pedido
        return await ver_detalle_pedido(update, context)
    
    if not query.data.startswith("estado_"):
        return CAMBIAR_ESTADO
    
    # Obtener nuevo estado
    estado_index = int(query.data.replace("estado_", ""))
    nuevo_estado = ESTADOS_PEDIDO[estado_index]
    
    # Importar aquí para evitar importación circular
    from utils.sheets import get_sheet_service, update_cell
    
    try:
        # Actualizar en Google Sheets
        fila = context.user_data.get('fila_pedido')
        id_pedido = context.user_data.get('pedido_actual')
        
        if not fila or not id_pedido:
            await query.edit_message_text("❌ Error: No se pudo identificar el pedido")
            return ConversationHandler.END
        
        # Actualizar columna O (índice 15, pero columna O es 15)
        success = await update_cell("PedidosWhatsApp", fila, 15, nuevo_estado)
        
        if success:
            # Agregar timestamp a observaciones
            ahora = datetime.now(peru_tz)
            timestamp = ahora.strftime("%d/%m %H:%M")
            usuario = update.effective_user.username or update.effective_user.first_name
            
            # Obtener observaciones actuales
            from utils.sheets import get_all_data
            pedidos = await get_all_data("PedidosWhatsApp")
            obs_actuales = ""
            
            if len(pedidos) > fila - 1 and len(pedidos[fila - 1]) > 16:
                obs_actuales = pedidos[fila - 1][16] or ""
            
            # Agregar nueva observación
            nueva_obs = f"[{timestamp}] Estado cambiado a '{nuevo_estado}' por {usuario}"
            if obs_actuales:
                nueva_obs = f"{nueva_obs}\n{obs_actuales}"
            
            # Limitar a 500 caracteres
            nueva_obs = nueva_obs[:500]
            
            # Actualizar observaciones (columna Q, índice 17)
            await update_cell("PedidosWhatsApp", fila, 17, nueva_obs)
            
            mensaje = f"""
✅ *ESTADO ACTUALIZADO*
━━━━━━━━━━━━━━━━━━━━━

Pedido: *{id_pedido}*
Nuevo estado: *{nuevo_estado}*
Actualizado por: @{usuario}
Hora: {timestamp}

_El cliente recibirá una notificación automática_
"""
            
            # Crear botones para siguiente acción
            keyboard = [
                [InlineKeyboardButton(f"🔄 Ver pedido actualizado", callback_data=f"ver_{id_pedido}")],
                [InlineKeyboardButton("📋 Ver más pedidos", callback_data="pw_volver_lista")],
                [InlineKeyboardButton("🏠 Menú principal", callback_data="pw_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                mensaje,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        else:
            await query.edit_message_text("❌ Error al actualizar el estado")
            
    except Exception as e:
        logger.error(f"Error cambiando estado: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")
    
    return ConversationHandler.END

async def agregar_nota(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Agrega una nota al pedido"""
    if not context.user_data.get('esperando_nota'):
        return CAMBIAR_ESTADO
    
    nota = update.message.text
    fila = context.user_data.get('fila_pedido')
    id_pedido = context.user_data.get('pedido_actual')
    
    # Importar aquí
    from utils.sheets import get_all_data, update_cell
    
    try:
        # Obtener observaciones actuales
        pedidos = await get_all_data("PedidosWhatsApp")
        obs_actuales = ""
        
        if len(pedidos) > fila - 1 and len(pedidos[fila - 1]) > 16:
            obs_actuales = pedidos[fila - 1][16] or ""
        
        # Agregar nueva nota
        ahora = datetime.now(peru_tz)
        timestamp = ahora.strftime("%d/%m %H:%M")
        usuario = update.effective_user.username or update.effective_user.first_name
        
        nueva_obs = f"[{timestamp}] Nota de {usuario}: {nota}"
        if obs_actuales:
            nueva_obs = f"{nueva_obs}\n{obs_actuales}"
        
        # Limitar a 500 caracteres
        nueva_obs = nueva_obs[:500]
        
        # Actualizar en Sheets
        success = await update_cell("PedidosWhatsApp", fila, 17, nueva_obs)
        
        if success:
            await update.message.reply_text(
                f"✅ Nota agregada al pedido *{id_pedido}*",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Error al agregar la nota")
            
    except Exception as e:
        logger.error(f"Error agregando nota: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    context.user_data['esperando_nota'] = False
    return ConversationHandler.END

async def buscar_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la búsqueda de pedidos por ID o WhatsApp"""
    texto = update.message.text.strip()
    filtro = context.user_data.get('filtro_pedidos', '')
    
    if filtro == "buscar_id":
        # Normalizar ID
        texto = texto.upper()
        if not texto.startswith("CAF-"):
            texto = f"CAF-{texto}"
        context.user_data['buscar_valor'] = texto
        context.user_data['filtro_pedidos'] = f"id_{texto}"
        
    elif filtro == "buscar_wa":
        # Normalizar WhatsApp
        texto = texto.replace("+", "").replace(" ", "").replace("-", "")
        if texto.startswith("51"):
            texto = texto[2:]
        context.user_data['buscar_valor'] = texto
        context.user_data['filtro_pedidos'] = f"wa_{texto}"
    
    # Mostrar resultados
    await mostrar_pedidos(update, context, context.user_data['filtro_pedidos'])
    return SELECCIONAR_PEDIDO

async def mostrar_estadisticas(query, context: ContextTypes.DEFAULT_TYPE):
    """Muestra estadísticas de los pedidos"""
    from utils.sheets import get_all_data
    
    try:
        pedidos = await get_all_data("PedidosWhatsApp")
        
        if not pedidos or len(pedidos) <= 1:
            await query.edit_message_text("📊 No hay datos para mostrar estadísticas")
            return
        
        # Calcular estadísticas
        total_pedidos = len(pedidos) - 1  # Menos el header
        
        # Contar por estado
        estados_count = {}
        total_ventas = 0
        total_kg = 0
        clientes_unicos = set()
        
        for pedido in pedidos[1:]:
            # Estado
            if len(pedido) > 14:
                estado = pedido[14] or "Sin estado"
                estados_count[estado] = estados_count.get(estado, 0) + 1
            
            # Total ventas
            if len(pedido) > 12:
                try:
                    total_ventas += float(pedido[12] or 0)
                except:
                    pass
            
            # Total kg
            if len(pedido) > 8:
                try:
                    total_kg += float(pedido[8] or 0)
                except:
                    pass
            
            # Clientes únicos
            if len(pedido) > 19:
                whatsapp = pedido[19]
                if whatsapp:
                    clientes_unicos.add(whatsapp)
        
        # Formatear mensaje
        mensaje = f"""
📊 *ESTADÍSTICAS DE PEDIDOS*
━━━━━━━━━━━━━━━━━━━━━

📦 *Total de pedidos:* {total_pedidos}
👥 *Clientes únicos:* {len(clientes_unicos)}
💰 *Total en ventas:* S/ {total_ventas:,.2f}
⚖️ *Total kg vendidos:* {total_kg:,.1f} kg

📈 *PEDIDOS POR ESTADO:*
"""
        
        for estado, count in sorted(estados_count.items(), key=lambda x: x[1], reverse=True):
            emoji = EMOJI_ESTADOS.get(estado, "📋")
            porcentaje = (count / total_pedidos) * 100
            mensaje += f"\n{emoji} {estado}: {count} ({porcentaje:.1f}%)"
        
        # Promedio por pedido
        if total_pedidos > 0:
            promedio_venta = total_ventas / total_pedidos
            promedio_kg = total_kg / total_pedidos
            
            mensaje += f"""

💡 *PROMEDIOS:*
• Venta promedio: S/ {promedio_venta:.2f}
• Cantidad promedio: {promedio_kg:.1f} kg
"""
        
        keyboard = [[InlineKeyboardButton("🔙 Volver al menú", callback_data="pw_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            mensaje,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error mostrando estadísticas: {e}")
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def volver_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Vuelve al menú principal"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "pw_menu":
        # Simular que se envió el comando inicial
        update.callback_query.message = update.callback_query.message
        return await pedidos_whatsapp_command(update.callback_query, context)
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual"""
    await update.message.reply_text("Operación cancelada.")
    return ConversationHandler.END

def register_pedidos_whatsapp_handlers(application):
    """Registra todos los handlers del módulo de pedidos WhatsApp"""
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('pedidos_whatsapp', pedidos_whatsapp_command)],
        states={
            SELECCIONAR_FILTRO: [
                CallbackQueryHandler(seleccionar_filtro, pattern='^pw_'),
                CallbackQueryHandler(volver_menu, pattern='^pw_menu$')
            ],
            MOSTRAR_PEDIDOS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, buscar_pedido),
                CallbackQueryHandler(volver_menu, pattern='^pw_')
            ],
            SELECCIONAR_PEDIDO: [
                CallbackQueryHandler(ver_detalle_pedido, pattern='^ver_'),
                CallbackQueryHandler(seleccionar_filtro, pattern='^pw_volver$'),
                CallbackQueryHandler(volver_menu, pattern='^pw_')
            ],
            CAMBIAR_ESTADO: [
                CallbackQueryHandler(cambiar_estado_pedido, pattern='^estado_'),
                CallbackQueryHandler(cambiar_estado_pedido, pattern='^pw_volver_lista$'),
                CallbackQueryHandler(cambiar_estado_pedido, pattern='^nota_pedido$'),
                CallbackQueryHandler(ver_detalle_pedido, pattern='^ver_'),
                CallbackQueryHandler(volver_menu, pattern='^pw_menu$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, agregar_nota)
            ]
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar),
            MessageHandler(filters.COMMAND, cancelar)
        ]
    )
    
    application.add_handler(conv_handler)
    
    # Handler para el comando directo de estadísticas
    application.add_handler(CommandHandler('estadisticas_whatsapp', mostrar_estadisticas_command))
    
    logger.info("✅ Handlers de pedidos WhatsApp registrados correctamente")

async def mostrar_estadisticas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando directo para mostrar estadísticas"""
    # Crear un query falso para reusar la función
    class FakeQuery:
        async def edit_message_text(self, *args, **kwargs):
            await update.message.reply_text(*args, **kwargs)
    
    await mostrar_estadisticas(FakeQuery(), context)

# Alias para compatibilidad
pedidoswhatsapp_command = pedidos_whatsapp_command
