"""
Módulo para gestionar precios personalizados por cliente desde Telegram
Permite agregar, editar y eliminar precios especiales en CatalogoPersonalizado
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

# Configurar zona horaria
peru_tz = pytz.timezone('America/Lima')

# Estados de conversación
MENU, SELECCIONAR_CLIENTE, SELECCIONAR_PRODUCTO, INGRESAR_PRECIO = range(4)

logger = logging.getLogger(__name__)

async def precios_personalizados_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando principal para gestionar precios personalizados"""
    context.user_data.clear()
    mensaje = """
*💎 PRECIOS PERSONALIZADOS*
━━━━━━━━━━━━━━━━━━━━━

Gestiona precios especiales para clientes VIP

Selecciona una opción:
"""
    keyboard = [
        [InlineKeyboardButton("➕ Agregar precio personalizado", callback_data="pp_agregar")],
        [InlineKeyboardButton("📋 Ver precios actuales", callback_data="pp_ver")],
        [InlineKeyboardButton("🗑️ Eliminar precio", callback_data="pp_eliminar")],
        [InlineKeyboardButton("❌ Salir", callback_data="pp_salir")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(mensaje, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.callback_query.edit_message_text(mensaje, reply_markup=reply_markup, parse_mode='Markdown')
    return MENU

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las opciones del menú principal"""
    query = update.callback_query
    await query.answer()
    opcion = query.data.replace("pp_", "")
    
    if opcion == "salir":
        await query.edit_message_text("✅ Gestión de precios finalizada")
        return ConversationHandler.END
    elif opcion == "volver":
        return await precios_personalizados_command(update, context)
    elif opcion == "ver":
        await query.edit_message_text("Cargando precios personalizados...")
        precios = obtener_precios_personalizados()
        if not precios:
            mensaje = "*📋 PRECIOS PERSONALIZADOS*\n━━━━━━━━━━━━━━━━━━━━━\n\n_No hay precios personalizados configurados_"
            keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data="pp_volver")]]
            await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return MENU
        mensaje = f"*📋 PRECIOS PERSONALIZADOS*\n━━━━━━━━━━━━━━━━━━━━━\n\nTotal: *{len(precios)}* precio(s) configurado(s)\n\n"
        for i, p in enumerate(precios[:10], 1):
            try:
                mensaje += f"*{i}. {p[1] if len(p) > 1 else '-'}*\n"
                mensaje += f"ID Producto: `{p[0] if len(p) > 0 else '-'}`\n"
                mensaje += f"Cliente: {p[3] if len(p) > 3 else '-'} (`{p[2] if len(p) > 2 else '-'}`)\n"
                mensaje += f"Precio: *S/{p[4] if len(p) > 4 else '-'}* /kg\n"
                mensaje += f"Estado: {p[6] if len(p) > 6 else 'ACTIVO'}\n━━━━━━━━━━━━━━━\n"
            except Exception as e:
                logger.error(f"Error formateando precio {i}: {e}")
        if len(precios) > 10:
            mensaje += f"\n_Mostrando 10 de {len(precios)} precios_\n"
        keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data="pp_volver")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MENU
    elif opcion == "agregar":
        await query.edit_message_text("Cargando clientes...")
        clientes = obtener_clientes_validados()
        if not clientes:
            mensaje = "❌ No hay clientes disponibles\n\n_Primero debes validar clientes con /clientes_"
            keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data="pp_volver")]]
            await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return MENU
        mensaje = "*➕ AGREGAR PRECIO PERSONALIZADO*\n━━━━━━━━━━━━━━━━━━━━━\n\nPaso 1: Selecciona el cliente"
        keyboard = []
        for cliente in clientes[:15]:
            id_cliente = cliente[0] if len(cliente) > 0 else ""
            empresa = cliente[3] if len(cliente) > 3 else (cliente[1] if len(cliente) > 1 else "Sin nombre")
            texto = empresa[:27] + "..." if len(empresa) > 30 else empresa
            keyboard.append([InlineKeyboardButton(texto, callback_data=f"cli_{id_cliente}")])
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="pp_volver")])
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return SELECCIONAR_CLIENTE
    elif opcion == "eliminar":
        await query.edit_message_text("Cargando precios personalizados...")
        precios = obtener_precios_personalizados()
        if not precios:
            mensaje = "❌ No hay precios personalizados para eliminar"
            keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data="pp_volver")]]
            await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return MENU
        mensaje = "*🗑️ ELIMINAR PRECIO PERSONALIZADO*\n━━━━━━━━━━━━━━━━━━━━━\n\nSelecciona el precio a eliminar:"
        keyboard = []
        context.user_data['precios_lista'] = []
        for i, p in enumerate(precios[:15], 1):
            try:
                texto = f"{p[3] if len(p) > 3 else '-'} - {p[1] if len(p) > 1 else '-'} (S/{p[4] if len(p) > 4 else '-'})"
                texto = texto[:37] + "..." if len(texto) > 40 else texto
                context.user_data['precios_lista'].append({'fila': i + 1, 'id_producto': p[0] if len(p) > 0 else '-', 'nombre_producto': p[1] if len(p) > 1 else '-', 'empresa': p[3] if len(p) > 3 else '-', 'precio': p[4] if len(p) > 4 else '-'})
                keyboard.append([InlineKeyboardButton(texto, callback_data=f"del_{i}")])
            except Exception as e:
                logger.error(f"Error listando precio {i}: {e}")
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="pp_volver")])
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return SELECCIONAR_CLIENTE

async def cliente_seleccionado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "pp_volver":
        return await precios_personalizados_command(update, context)
    if query.data.startswith("del_"):
        indice = int(query.data.replace("del_", ""))
        precios_lista = context.user_data.get('precios_lista', [])
        if indice > len(precios_lista):
            await query.edit_message_text("❌ Error: Precio no encontrado")
            return MENU
        precio_info = precios_lista[indice - 1]
        mensaje = f"*⚠️ CONFIRMAR ELIMINACIÓN*\n━━━━━━━━━━━━━━━━━━━━━\n\nCliente: *{precio_info['empresa']}*\nProducto: *{precio_info['nombre_producto']}*\nPrecio: S/{precio_info['precio']}\n\n¿Estás seguro de eliminar este precio personalizado?"
        keyboard = [[InlineKeyboardButton("✅ Sí, eliminar", callback_data=f"confirm_del_{precio_info['fila']}")], [InlineKeyboardButton("❌ No, cancelar", callback_data="pp_volver")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return SELECCIONAR_CLIENTE
    if query.data.startswith("confirm_del_"):
        fila = int(query.data.replace("confirm_del_", ""))
        await query.edit_message_text("Eliminando precio...")
        exito = eliminar_precio_personalizado(fila)
        if exito:
            mensaje = "✅ *PRECIO ELIMINADO CORRECTAMENTE*\n━━━━━━━━━━━━━━━━━━━━━\n\nEl precio personalizado ha sido eliminado."
        else:
            mensaje = "❌ *ERROR AL ELIMINAR*\n━━━━━━━━━━━━━━━━━━━━━\n\nNo se pudo eliminar el precio."
        keyboard = [[InlineKeyboardButton("🗑️ Eliminar otro", callback_data="pp_eliminar")], [InlineKeyboardButton("↩️ Menú principal", callback_data="pp_volver")]]
        await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return MENU
    id_cliente = query.data.replace("cli_", "")
    context.user_data['telefono_cliente'] = id_cliente
    info_cliente = obtener_info_cliente(id_cliente)
    if not info_cliente:
        await query.edit_message_text("Error: Cliente no encontrado")
        return MENU
    context.user_data['nombre_cliente'] = info_cliente['nombre']
    context.user_data['empresa_cliente'] = info_cliente.get('empresa', '')
    await query.edit_message_text("Cargando productos...")
    productos = obtener_catalogo_productos()
    if not productos:
        await query.edit_message_text("❌ No hay productos disponibles")
        return MENU
    mensaje = f"*➕ AGREGAR PRECIO PERSONALIZADO*\n━━━━━━━━━━━━━━━━━━━━━\n\nCliente: *{info_cliente['nombre']}*\n{info_cliente.get('empresa', '')}\n\nPaso 2: Selecciona el producto"
    keyboard = []
    for prod in productos[:10]:
        texto = f"{prod[1]} (S/{prod[2]})"
        texto = texto[:32] + "..." if len(texto) > 35 else texto
        keyboard.append([InlineKeyboardButton(texto, callback_data=f"prod_{prod[0]}")])
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="pp_volver")])
    await query.edit_message_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return SELECCIONAR_PRODUCTO

async def producto_seleccionado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == "pp_volver":
        return await precios_personalizados_command(update, context)
    id_producto = query.data.replace("prod_", "")
    context.user_data['id_producto'] = id_producto
    info_producto = obtener_info_producto(id_producto)
    if not info_producto:
        await query.edit_message_text("Error: Producto no encontrado")
        return MENU
    context.user_data['nombre_producto'] = info_producto['nombre']
    context.user_data['precio_normal'] = info_producto['precio']
    mensaje = f"*➕ AGREGAR PRECIO PERSONALIZADO*\n━━━━━━━━━━━━━━━━━━━━━\n\nCliente: *{context.user_data['nombre_cliente']}*\nProducto: *{info_producto['nombre']}*\nPrecio normal: S/{info_producto['precio']}\n\nPaso 3: Ingresa el precio VIP\nEjemplo: `28.50`\n\n_Escribe /cancelar para salir_"
    await query.edit_message_text(mensaje, parse_mode='Markdown')
    return INGRESAR_PRECIO

async def procesar_precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    texto = update.message.text.strip()
    try:
        precio_vip = float(texto)
        if precio_vip < 0:
            await update.message.reply_text("❌ El precio debe ser mayor o igual a 0")
            return INGRESAR_PRECIO
    except ValueError:
        await update.message.reply_text("❌ Por favor, envía solo el número\nEjemplo: 28.50")
        return INGRESAR_PRECIO
    telefono = context.user_data.get('telefono_cliente')
    nombre_cliente = context.user_data.get('nombre_cliente')
    empresa = context.user_data.get('empresa_cliente', '')
    id_producto = context.user_data.get('id_producto')
    nombre_producto = context.user_data.get('nombre_producto')
    precio_normal = float(context.user_data.get('precio_normal', 0))
    if precio_vip >= precio_normal:
        await update.message.reply_text(f"⚠️ El precio VIP (S/{precio_vip}) debe ser menor al precio normal (S/{precio_normal})\n\nIntenta con un precio más bajo")
        return INGRESAR_PRECIO
    await update.message.reply_text("Guardando precio personalizado...")
    exito = agregar_precio_personalizado(telefono, nombre_cliente, empresa, id_producto, nombre_producto, precio_normal, precio_vip)
    if exito:
        descuento = precio_normal - precio_vip
        porcentaje = (descuento / precio_normal) * 100
        mensaje = f"✅ *PRECIO PERSONALIZADO AGREGADO*\n━━━━━━━━━━━━━━━━━━━━━\n\nCliente: *{nombre_cliente}*\n{empresa}\n\nProducto: *{nombre_producto}*\nPrecio normal: S/{precio_normal}\nPrecio VIP: S/{precio_vip}\n\n💰 Descuento: S/{descuento:.2f} ({porcentaje:.0f}%)"
        keyboard = [[InlineKeyboardButton("➕ Agregar otro", callback_data="pp_agregar")], [InlineKeyboardButton("📋 Ver todos", callback_data="pp_ver")], [InlineKeyboardButton("↩️ Menú principal", callback_data="pp_volver")]]
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Error al guardar el precio personalizado\n\nIntenta nuevamente más tarde")
    return MENU

def obtener_clientes_validados():
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        if not service:
            return []
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='Clientes!A:F').execute()
        values = result.get('values', [])
        if len(values) <= 1:
            return []
        return [row for row in values[1:] if len(row) > 0]
    except Exception as e:
        logger.error(f"Error obteniendo clientes: {e}")
        return []

def obtener_info_cliente(telefono):
    try:
        clientes = obtener_clientes_validados()
        for c in clientes:
            if (c[0] if len(c) > 0 else "") == telefono or (c[2] if len(c) > 2 else "") == telefono:
                return {'id_cliente': c[0] if len(c) > 0 else '', 'nombre': c[1] if len(c) > 1 else 'Sin nombre', 'telefono': c[2] if len(c) > 2 else '', 'empresa': c[3] if len(c) > 3 else '', 'email': c[4] if len(c) > 4 else '', 'estado': c[5] if len(c) > 5 else 'ACTIVO'}
        return None
    except Exception as e:
        logger.error(f"Error obteniendo info del cliente: {e}")
        return None

def obtener_catalogo_productos():
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        if not service:
            return []
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='CatalogoWhatsApp!A:I').execute()
        values = result.get('values', [])
        if len(values) <= 1:
            return []
        return [row for row in values[1:] if len(row) > 8 and row[8] == 'ACTIVO']
    except Exception as e:
        logger.error(f"Error obteniendo catálogo: {e}")
        return []

def obtener_info_producto(id_producto):
    try:
        productos = obtener_catalogo_productos()
        for p in productos:
            if p[0] == id_producto:
                return {'id': p[0], 'nombre': p[1] if len(p) > 1 else 'Sin nombre', 'precio': p[2] if len(p) > 2 else '0'}
        return None
    except Exception as e:
        logger.error(f"Error obteniendo info del producto: {e}")
        return None

def obtener_precios_personalizados():
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        if not service:
            return []
        result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range='CatalogoPersonalizado!A:H').execute()
        values = result.get('values', [])
        if len(values) <= 1:
            return []
        return values[1:]
    except Exception as e:
        logger.error(f"Error obteniendo precios personalizados: {e}")
        return []

def agregar_precio_personalizado(telefono, nombre_cliente, empresa, id_producto, nombre_producto, precio_normal, precio_vip):
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        if not service:
            return False
        ahora = datetime.now(peru_tz)
        fecha_modificacion = ahora.strftime("%d/%m/%Y, %I:%M:%S %p")
        nueva_fila = [id_producto, nombre_producto, telefono, empresa or nombre_cliente, str(precio_vip), "", "ACTIVO", fecha_modificacion]
        body = {'values': [nueva_fila]}
        service.spreadsheets().values().append(spreadsheetId=SPREADSHEET_ID, range='CatalogoPersonalizado!A:H', valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS', body=body).execute()
        logger.info(f"Precio personalizado agregado: {id_producto} - {empresa} - S/{precio_vip}")
        return True
    except Exception as e:
        logger.error(f"Error agregando precio personalizado: {e}")
        return False

def eliminar_precio_personalizado(fila):
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        if not service:
            return False
        request = {'deleteDimension': {'range': {'sheetId': obtener_sheet_id('CatalogoPersonalizado'), 'dimension': 'ROWS', 'startIndex': fila, 'endIndex': fila + 1}}}
        body = {'requests': [request]}
        service.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
        logger.info(f"Precio personalizado eliminado de fila {fila}")
        return True
    except Exception as e:
        logger.error(f"Error eliminando precio personalizado: {e}")
        return False

def obtener_sheet_id(nombre_hoja):
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        if not service:
            return 0
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        for sheet in spreadsheet['sheets']:
            if sheet['properties']['title'] == nombre_hoja:
                return sheet['properties']['sheetId']
        return 0
    except Exception as e:
        logger.error(f"Error obteniendo sheet ID: {e}")
        return 0

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    keyboard = [[InlineKeyboardButton("↩️ Volver al menú", callback_data="pp_volver")]]
    await update.message.reply_text("Operación cancelada", reply_markup=InlineKeyboardMarkup(keyboard))
    return MENU

def register_precios_personalizados_handlers(application):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('precios_personalizados', precios_personalizados_command), CommandHandler('precios_vip', precios_personalizados_command), CommandHandler('pvip', precios_personalizados_command)],
        states={
            MENU: [CallbackQueryHandler(menu_callback, pattern='^pp_'), CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$'), MessageHandler(filters.COMMAND, cancelar)],
            SELECCIONAR_CLIENTE: [CallbackQueryHandler(cliente_seleccionado, pattern='^cli_'), CallbackQueryHandler(cliente_seleccionado, pattern='^del_'), CallbackQueryHandler(cliente_seleccionado, pattern='^confirm_del_'), CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$'), MessageHandler(filters.COMMAND, cancelar)],
            SELECCIONAR_PRODUCTO: [CallbackQueryHandler(producto_seleccionado, pattern='^prod_'), CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$'), MessageHandler(filters.COMMAND, cancelar)],
            INGRESAR_PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_precio), MessageHandler(filters.COMMAND, cancelar)]
        },
        fallbacks=[CommandHandler('cancelar', cancelar), CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$')],
        conversation_timeout=300
    )
    application.add_handler(conv_handler)
    logger.info("Handlers de precios personalizados registrados correctamente")