"""
Módulo mejorado para administrar el catálogo de WhatsApp desde Telegram
Versión con interfaz más intuitiva
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
MENU, SELECCIONAR_PRODUCTO, INGRESAR_VALOR = range(3)

logger = logging.getLogger(__name__)

async def catalogo_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando principal para administrar el catálogo"""
    
    # Limpiar contexto
    context.user_data.clear()
    
    # Obtener catálogo actual para mostrarlo
    productos = obtener_catalogo_productos()
    
    # Formatear mensaje con el catálogo
    mensaje = "*ADMINISTRACIÓN DE CATÁLOGO*\n"
    mensaje += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if productos:
        mensaje += "*📦 PRODUCTOS ACTUALES:*\n\n"
        
        for p in productos[:10]:  # Máximo 10 productos
            try:
                nombre = p[1]
                precio = p[2]
                stock = p[6]
                estado = p[8]
                
                if estado == 'ACTIVO':
                    mensaje += f"• *{nombre}*\n"
                    mensaje += f"  S/{precio}/kg | Stock: {stock}kg\n\n"
            except:
                continue
        
        if len(productos) > 10:
            mensaje += f"_...y {len(productos)-10} productos más_\n\n"
    else:
        mensaje += "_No hay productos en el catálogo_\n\n"
    
    mensaje += "━━━━━━━━━━━━━━━━\n"
    mensaje += "Selecciona una opción:"
    
    keyboard = [
        [InlineKeyboardButton("💰 Actualizar precio", callback_data="cat_precio")],
        [InlineKeyboardButton("📦 Actualizar stock", callback_data="cat_stock")],
        [InlineKeyboardButton("❌ Salir", callback_data="cat_salir")]
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
    
    return MENU

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las opciones del menú principal"""
    query = update.callback_query
    await query.answer()
    
    opcion = query.data.replace("cat_", "")
    
    if opcion == "salir":
        await query.edit_message_text("✅ Administración de catálogo finalizada")
        return ConversationHandler.END
    
    elif opcion == "volver":
        return await catalogo_admin_command(update, context)
    
    elif opcion in ["precio", "stock"]:
        # Guardar la acción en el contexto
        context.user_data['accion'] = opcion
        
        # Mostrar lista de productos para seleccionar
        await query.edit_message_text("Cargando productos...")
        
        productos = obtener_catalogo_productos()
        
        if not productos:
            await query.edit_message_text("No hay productos disponibles")
            return MENU
        
        # Crear título según la acción
        if opcion == "precio":
            titulo = "*💰 ACTUALIZAR PRECIO*\n━━━━━━━━━━━━━━━━\n\nSelecciona el producto:"
        else:
            titulo = "*📦 ACTUALIZAR STOCK*\n━━━━━━━━━━━━━━━━\n\nSelecciona el producto:"
        
        # Crear botones con los productos
        keyboard = []
        for p in productos[:10]:  # Máximo 10 productos
            try:
                id_prod = p[0]
                nombre = p[1]
                precio = p[2]
                stock = p[6]
                estado = p[8]
                
                if estado == 'ACTIVO':
                    # Texto del botón con info actual
                    if opcion == "precio":
                        texto_boton = f"{nombre} (S/{precio})"
                    else:
                        texto_boton = f"{nombre} ({stock}kg)"
                    
                    # Limitar longitud del botón
                    if len(texto_boton) > 35:
                        texto_boton = texto_boton[:32] + "..."
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            texto_boton,
                            callback_data=f"prod_{id_prod}"
                        )
                    ])
            except:
                continue
        
        # Agregar botón de cancelar
        keyboard.append([InlineKeyboardButton("Cancelar", callback_data="cat_volver")])
        
        await query.edit_message_text(
            titulo,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return SELECCIONAR_PRODUCTO

async def producto_seleccionado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de un producto"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cat_volver":
        return await catalogo_admin_command(update, context)
    
    # Extraer ID del producto
    id_producto = query.data.replace("prod_", "")
    
    # Guardar en contexto
    context.user_data['producto_id'] = id_producto
    
    # Obtener información del producto
    producto_info = obtener_info_producto(id_producto)
    
    if not producto_info:
        await query.edit_message_text("Error: Producto no encontrado")
        return MENU
    
    nombre = producto_info.get('nombre', 'Producto')
    precio_actual = producto_info.get('precio', '0')
    stock_actual = producto_info.get('stock', '0')
    
    # Guardar info en contexto
    context.user_data['producto_nombre'] = nombre
    context.user_data['valor_actual'] = precio_actual if context.user_data['accion'] == 'precio' else stock_actual
    
    # Crear mensaje según la acción
    if context.user_data['accion'] == 'precio':
        mensaje = f"""
*ACTUALIZAR PRECIO*
━━━━━━━━━━━━━━━━

Producto: *{nombre}*
Precio actual: *S/{precio_actual}*

Envía el nuevo precio (solo el número):
Ejemplo: `35.50`

_Escribe /cancelar para salir_
"""
    else:
        mensaje = f"""
*ACTUALIZAR STOCK*
━━━━━━━━━━━━━━━━

Producto: *{nombre}*
Stock actual: *{stock_actual} kg*

Envía la nueva cantidad (solo el número):
Ejemplo: `150`

_Escribe /cancelar para salir_
"""
    
    await query.edit_message_text(mensaje, parse_mode='Markdown')
    
    return INGRESAR_VALOR

async def procesar_valor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el nuevo valor ingresado"""
    texto = update.message.text.strip()
    
    # Validar que sea un número
    try:
        valor_num = float(texto)
        if valor_num < 0:
            await update.message.reply_text("El valor debe ser mayor o igual a 0")
            return INGRESAR_VALOR
    except ValueError:
        await update.message.reply_text(
            "Por favor, envía solo el número\n"
            "Ejemplo: 35.50"
        )
        return INGRESAR_VALOR
    
    # Obtener datos del contexto
    id_producto = context.user_data.get('producto_id')
    nombre_producto = context.user_data.get('producto_nombre')
    accion = context.user_data.get('accion')
    valor_anterior = context.user_data.get('valor_actual')
    
    await update.message.reply_text("Actualizando...")
    
    # Actualizar en Google Sheets
    exito = False
    if accion == 'precio':
        exito = actualizar_precio_producto(id_producto, valor_num)
        campo = "precio"
        unidad = "soles/kg"
    else:
        exito = actualizar_stock_producto(id_producto, valor_num)
        campo = "stock"
        unidad = "kg"
    
    if exito:
        # Crear emoji según el cambio
        if float(valor_anterior) < valor_num:
            emoji_cambio = "📈"
        elif float(valor_anterior) > valor_num:
            emoji_cambio = "📉"
        else:
            emoji_cambio = "➡️"
        
        mensaje = f"""
✅ *ACTUALIZACIÓN EXITOSA*
━━━━━━━━━━━━━━━━━━

Producto: *{nombre_producto}*
{campo.capitalize()} anterior: {valor_anterior} {unidad}
{campo.capitalize()} nuevo: {valor_num} {unidad}
{emoji_cambio} Cambio aplicado

_Los cambios se reflejarán inmediatamente en WhatsApp_
"""
        
        keyboard = [
            [InlineKeyboardButton("Ver catálogo actualizado", callback_data="cat_volver")],
            [InlineKeyboardButton("Otra actualización", callback_data="cat_volver")],
            [InlineKeyboardButton("Salir", callback_data="cat_salir")]
        ]
        
        await update.message.reply_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ Error al actualizar {campo}\n\n"
            "Intenta nuevamente más tarde"
        )
    
    return MENU

def obtener_catalogo_productos():
    """Obtiene los productos del catálogo desde Google Sheets"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            return []
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='CatalogoWhatsApp!A:I'
        ).execute()
        
        values = result.get('values', [])
        
        if len(values) <= 1:
            return []
        
        # Retornar productos con datos
        return [row for row in values[1:] if len(row) > 0 and row[0]]
        
    except Exception as e:
        logger.error(f"Error obteniendo catálogo: {e}")
        return []

def obtener_info_producto(id_producto):
    """Obtiene información detallada de un producto"""
    try:
        productos = obtener_catalogo_productos()
        
        for p in productos:
            if p[0] == id_producto:
                return {
                    'id': p[0],
                    'nombre': p[1] if len(p) > 1 else 'Sin nombre',
                    'precio': p[2] if len(p) > 2 else '0',
                    'origen': p[3] if len(p) > 3 else 'No especificado',
                    'puntaje': p[4] if len(p) > 4 else '0',
                    'agricultor': p[5] if len(p) > 5 else 'No especificado',
                    'stock': p[6] if len(p) > 6 else '0',
                    'descripcion': p[7] if len(p) > 7 else '',
                    'estado': p[8] if len(p) > 8 else 'ACTIVO'
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo info del producto: {e}")
        return None

def actualizar_precio_producto(id_producto, nuevo_precio):
    """Actualiza el precio de un producto"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            return False
        
        # Obtener todos los productos
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='CatalogoWhatsApp!A:J'
        ).execute()
        
        values = result.get('values', [])
        
        # Buscar el producto
        for i, row in enumerate(values[1:], start=2):
            if len(row) > 0 and row[0] == id_producto:
                # Actualizar precio (columna C)
                range_precio = f'CatalogoWhatsApp!C{i}'
                body = {'values': [[str(nuevo_precio)]]}
                
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=range_precio,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                
                # Actualizar fecha modificación (columna J)
                ahora = datetime.now(peru_tz)
                fecha = ahora.strftime("%d/%m/%Y %H:%M")
                
                range_fecha = f'CatalogoWhatsApp!J{i}'
                body_fecha = {'values': [[fecha]]}
                
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=range_fecha,
                    valueInputOption='USER_ENTERED',
                    body=body_fecha
                ).execute()
                
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error actualizando precio: {e}")
        return False

def actualizar_stock_producto(id_producto, nuevo_stock):
    """Actualiza el stock de un producto"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            return False
        
        # Obtener todos los productos
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='CatalogoWhatsApp!A:J'
        ).execute()
        
        values = result.get('values', [])
        
        # Buscar el producto
        for i, row in enumerate(values[1:], start=2):
            if len(row) > 0 and row[0] == id_producto:
                # Actualizar stock (columna G)
                range_stock = f'CatalogoWhatsApp!G{i}'
                body = {'values': [[str(nuevo_stock)]]}
                
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=range_stock,
                    valueInputOption='USER_ENTERED',
                    body=body
                ).execute()
                
                # Actualizar fecha modificación (columna J)
                ahora = datetime.now(peru_tz)
                fecha = ahora.strftime("%d/%m/%Y %H:%M")
                
                range_fecha = f'CatalogoWhatsApp!J{i}'
                body_fecha = {'values': [[fecha]]}
                
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=range_fecha,
                    valueInputOption='USER_ENTERED',
                    body=body_fecha
                ).execute()
                
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error actualizando stock: {e}")
        return False

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual"""
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("Volver al menú", callback_data="cat_volver")]]
    
    await update.message.reply_text(
        "Operación cancelada",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU

def register_catalogo_admin_handlers(application):
    """Registra los handlers del módulo de administración de catálogo"""
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('catalogo_admin', catalogo_admin_command),
            CommandHandler('catalogo', catalogo_admin_command)
        ],
        states={
            MENU: [
                CallbackQueryHandler(menu_callback, pattern='^cat_'),
                CallbackQueryHandler(catalogo_admin_command, pattern='^cat_volver$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            SELECCIONAR_PRODUCTO: [
                CallbackQueryHandler(producto_seleccionado, pattern='^prod_'),
                CallbackQueryHandler(catalogo_admin_command, pattern='^cat_volver$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            INGRESAR_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_valor),
                MessageHandler(filters.COMMAND, cancelar)
            ]
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar),
            CallbackQueryHandler(catalogo_admin_command, pattern='^cat_volver$')
        ]
    )
    
    application.add_handler(conv_handler)
    logger.info("Handlers de administración de catálogo registrados correctamente")