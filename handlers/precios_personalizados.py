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
    
    # Limpiar contexto
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
            mensaje = """
*📋 PRECIOS PERSONALIZADOS*
━━━━━━━━━━━━━━━━━━━━━

_No hay precios personalizados configurados_
"""
            keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data="pp_volver")]]
            await query.edit_message_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return MENU
        
        # Construir mensaje con TODA la información
        mensaje = "*📋 PRECIOS PERSONALIZADOS*\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        mensaje += f"Total: *{len(precios)}* precio(s) configurado(s)\n\n"
        
        for i, p in enumerate(precios[:10], 1):  # Máximo 10 precios
            try:
                # Leer todas las columnas según la estructura del Excel
                id_producto = p[0] if len(p) > 0 else "-"
                nombre_producto = p[1] if len(p) > 1 else "-"
                id_cliente = p[2] if len(p) > 2 else "-"
                empresa = p[3] if len(p) > 3 else "-"
                precio_kg = p[4] if len(p) > 4 else "-"
                descripcion = p[5] if len(p) > 5 else "-"
                estado = p[6] if len(p) > 6 else "ACTIVO"
                ultima_mod = p[7] if len(p) > 7 else "-"
                
                # Formatear mensaje
                mensaje += f"*{i}. {nombre_producto}*\n"
                mensaje += f"ID Producto: `{id_producto}`\n"
                mensaje += f"Cliente: {empresa} (`{id_cliente}`)\n"
                mensaje += f"Precio: *S/{precio_kg}* /kg\n"
                
                # Solo mostrar descripción si no es muy larga
                if descripcion and descripcion != "-" and len(descripcion) < 50:
                    mensaje += f"_{descripcion}_\n"
                
                mensaje += f"Estado: {estado}\n"
                mensaje += f"━━━━━━━━━━━━━━━\n"
                
            except Exception as e:
                logger.error(f"Error formateando precio {i}: {e}")
                continue
        
        if len(precios) > 10:
            mensaje += f"\n_Mostrando 10 de {len(precios)} precios_\n"
        
        keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data="pp_volver")]]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MENU
    
    elif opcion == "agregar":
        context.user_data['accion'] = 'agregar'
        
        await query.edit_message_text("Cargando clientes...")
        
        # Obtener lista de clientes validados
        clientes = obtener_clientes_validados()
        
        if not clientes:
            mensaje = """
❌ No hay clientes disponibles

_Primero debes validar clientes con /clientes_
"""
            keyboard = [[InlineKeyboardButton("↩️ Volver", callback_data="pp_volver")]]
            await query.edit_message_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return MENU
        
        mensaje = """
*➕ AGREGAR PRECIO PERSONALIZADO*
━━━━━━━━━━━━━━━━━━━━━

Paso 1: Selecciona el cliente
"""
        
        keyboard = []
        for cliente in clientes[:10]:  # Máximo 10 clientes
            telefono = cliente[0]
            nombre = cliente[1]
            empresa = cliente[2] if len(cliente) > 2 else ""
            
            texto = f"{empresa or nombre}"
            if len(texto) > 30:
                texto = texto[:27] + "..."
            
            keyboard.append([
                InlineKeyboardButton(
                    texto,
                    callback_data=f"cli_{telefono}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="pp_volver")])
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return SELECCIONAR_CLIENTE
    
    elif opcion == "eliminar":
        await query.edit_message_text("⚠️ Función en desarrollo")
        return MENU

async def cliente_seleccionado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de un cliente"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "pp_volver":
        return await precios_personalizados_command(update, context)
    
    # Extraer teléfono del cliente
    telefono = query.data.replace("cli_", "")
    
    # Guardar en contexto
    context.user_data['telefono_cliente'] = telefono
    
    # Obtener info del cliente
    info_cliente = obtener_info_cliente(telefono)
    if not info_cliente:
        await query.edit_message_text("Error: Cliente no encontrado")
        return MENU
    
    context.user_data['nombre_cliente'] = info_cliente['nombre']
    context.user_data['empresa_cliente'] = info_cliente.get('empresa', '')
    
    # Mostrar productos disponibles
    await query.edit_message_text("Cargando productos...")
    
    productos = obtener_catalogo_productos()
    
    if not productos:
        await query.edit_message_text("❌ No hay productos disponibles")
        return MENU
    
    mensaje = f"""
*➕ AGREGAR PRECIO PERSONALIZADO*
━━━━━━━━━━━━━━━━━━━━━

Cliente: *{info_cliente['nombre']}*
{info_cliente.get('empresa', '')}

Paso 2: Selecciona el producto
"""
    
    keyboard = []
    for prod in productos[:10]:  # Máximo 10 productos
        id_prod = prod[0]
        nombre = prod[1]
        precio = prod[2]
        
        texto = f"{nombre} (S/{precio})"
        if len(texto) > 35:
            texto = texto[:32] + "..."
        
        keyboard.append([
            InlineKeyboardButton(
                texto,
                callback_data=f"prod_{id_prod}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="pp_volver")])
    
    await query.edit_message_text(
        mensaje,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return SELECCIONAR_PRODUCTO

async def producto_seleccionado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de un producto"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "pp_volver":
        return await precios_personalizados_command(update, context)
    
    # Extraer ID del producto
    id_producto = query.data.replace("prod_", "")
    
    # Guardar en contexto
    context.user_data['id_producto'] = id_producto
    
    # Obtener info del producto
    info_producto = obtener_info_producto(id_producto)
    
    if not info_producto:
        await query.edit_message_text("Error: Producto no encontrado")
        return MENU
    
    context.user_data['nombre_producto'] = info_producto['nombre']
    context.user_data['precio_normal'] = info_producto['precio']
    
    mensaje = f"""
*➕ AGREGAR PRECIO PERSONALIZADO*
━━━━━━━━━━━━━━━━━━━━━

Cliente: *{context.user_data['nombre_cliente']}*
Producto: *{info_producto['nombre']}*
Precio normal: S/{info_producto['precio']}

Paso 3: Ingresa el precio VIP
Ejemplo: `28.50`

_Escribe /cancelar para salir_
"""
    
    await query.edit_message_text(mensaje, parse_mode='Markdown')
    
    return INGRESAR_PRECIO

async def procesar_precio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el precio VIP ingresado"""
    texto = update.message.text.strip()
    
    # Validar que sea un número
    try:
        precio_vip = float(texto)
        if precio_vip < 0:
            await update.message.reply_text("❌ El precio debe ser mayor o igual a 0")
            return INGRESAR_PRECIO
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, envía solo el número\n"
            "Ejemplo: 28.50"
        )
        return INGRESAR_PRECIO
    
    # Obtener datos del contexto
    telefono = context.user_data.get('telefono_cliente')
    nombre_cliente = context.user_data.get('nombre_cliente')
    empresa = context.user_data.get('empresa_cliente', '')
    id_producto = context.user_data.get('id_producto')
    nombre_producto = context.user_data.get('nombre_producto')
    precio_normal = float(context.user_data.get('precio_normal', 0))
    
    # Validar que el precio VIP sea menor al normal
    if precio_vip >= precio_normal:
        await update.message.reply_text(
            f"⚠️ El precio VIP (S/{precio_vip}) debe ser menor al precio normal (S/{precio_normal})\n\n"
            "Intenta con un precio más bajo"
        )
        return INGRESAR_PRECIO
    
    await update.message.reply_text("Guardando precio personalizado...")
    
    # Guardar en Google Sheets
    exito = agregar_precio_personalizado(
        telefono=telefono,
        nombre_cliente=nombre_cliente,
        empresa=empresa,
        id_producto=id_producto,
        nombre_producto=nombre_producto,
        precio_normal=precio_normal,
        precio_vip=precio_vip
    )
    
    if exito:
        descuento = precio_normal - precio_vip
        porcentaje = (descuento / precio_normal) * 100
        
        mensaje = f"""
✅ *PRECIO PERSONALIZADO AGREGADO*
━━━━━━━━━━━━━━━━━━━━━

Cliente: *{nombre_cliente}*
{empresa}

Producto: *{nombre_producto}*
Precio normal: S/{precio_normal}
Precio VIP: S/{precio_vip}

💰 Descuento: S/{descuento:.2f} ({porcentaje:.0f}%)

_El cliente verá este precio en WhatsApp_
"""
        
        keyboard = [
            [InlineKeyboardButton("➕ Agregar otro", callback_data="pp_agregar")],
            [InlineKeyboardButton("📋 Ver todos", callback_data="pp_ver")],
            [InlineKeyboardButton("↩️ Menú principal", callback_data="pp_volver")]
        ]
        
        await update.message.reply_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Error al guardar el precio personalizado\n\n"
            "Intenta nuevamente más tarde"
        )
    
    return MENU

def obtener_clientes_validados():
    """Obtiene la lista de clientes desde la pestaña Clientes"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            return []
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='Clientes!A:F'  # Leer desde la pestaña Clientes
        ).execute()
        
        values = result.get('values', [])
        
        if len(values) <= 1:
            return []
        
        # Retornar todos los clientes (sin filtro de estado)
        return [row for row in values[1:] if len(row) > 0]
        
    except Exception as e:
        logger.error(f"Error obteniendo clientes: {e}")
        return []

def obtener_info_cliente(telefono):
    """Obtiene información de un cliente desde la pestaña Clientes"""
    try:
        clientes = obtener_clientes_validados()
        
        for c in clientes:
            # Buscar por ID_Cliente (columna A) o Teléfono (columna C)
            id_cliente = c[0] if len(c) > 0 else ""
            telefono_col = c[2] if len(c) > 2 else ""
            
            if id_cliente == telefono or telefono_col == telefono:
                return {
                    'id_cliente': c[0] if len(c) > 0 else '',
                    'nombre': c[1] if len(c) > 1 else 'Sin nombre',
                    'telefono': c[2] if len(c) > 2 else '',
                    'empresa': c[3] if len(c) > 3 else '',
                    'email': c[4] if len(c) > 4 else '',
                    'estado': c[5] if len(c) > 5 else 'ACTIVO'
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo info del cliente: {e}")
        return None

def obtener_catalogo_productos():
    """Obtiene los productos del catálogo"""
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
        
        # Retornar productos activos
        return [row for row in values[1:] if len(row) > 8 and row[8] == 'ACTIVO']
        
    except Exception as e:
        logger.error(f"Error obteniendo catálogo: {e}")
        return []

def obtener_info_producto(id_producto):
    """Obtiene información de un producto"""
    try:
        productos = obtener_catalogo_productos()
        
        for p in productos:
            if p[0] == id_producto:
                return {
                    'id': p[0],
                    'nombre': p[1] if len(p) > 1 else 'Sin nombre',
                    'precio': p[2] if len(p) > 2 else '0'
                }
        
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo info del producto: {e}")
        return None

def obtener_precios_personalizados():
    """Obtiene todos los precios personalizados"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            return []
        
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range='CatalogoPersonalizado!A:H'  # Leer hasta la columna H
        ).execute()
        
        values = result.get('values', [])
        
        if len(values) <= 1:
            return []
        
        return values[1:]  # Saltar el header
        
    except Exception as e:
        logger.error(f"Error obteniendo precios personalizados: {e}")
        return []

def agregar_precio_personalizado(telefono, nombre_cliente, empresa, id_producto, 
                                 nombre_producto, precio_normal, precio_vip):
    """Agrega un nuevo precio personalizado"""
    try:
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        
        if not service:
            return False
        
        # Preparar datos según la estructura: A-H
        # A: ID_Producto, B: Nombre, C: ID Cliente, D: Empresa/Negocio, 
        # E: Precio_Kg, F: Descripcion, G: Estado, H: Ultima_Modificacion
        ahora = datetime.now(peru_tz)
        fecha_modificacion = ahora.strftime("%d/%m/%Y, %I:%M:%S %p")
        
        nueva_fila = [
            id_producto,           # A: ID_Producto
            nombre_producto,       # B: Nombre
            telefono,              # C: ID Cliente (teléfono)
            empresa or nombre_cliente,  # D: Empresa/Negocio
            str(precio_vip),       # E: Precio_Kg (precio VIP)
            "",                    # F: Descripcion (vacío por ahora)
            "ACTIVO",              # G: Estado
            fecha_modificacion     # H: Ultima_Modificacion
        ]
        
        # Agregar a la hoja
        body = {'values': [nueva_fila]}
        
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='CatalogoPersonalizado!A:H',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        
        logger.info(f"Precio personalizado agregado: {id_producto} - {empresa} - S/{precio_vip}")
        return True
        
    except Exception as e:
        logger.error(f"Error agregando precio personalizado: {e}")
        return False

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la operación actual"""
    context.user_data.clear()
    
    keyboard = [[InlineKeyboardButton("↩️ Volver al menú", callback_data="pp_volver")]]
    
    await update.message.reply_text(
        "Operación cancelada",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU

def register_precios_personalizados_handlers(application):
    """Registra los handlers del módulo de precios personalizados"""
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('precios_personalizados', precios_personalizados_command),
            CommandHandler('precios_vip', precios_personalizados_command),
            CommandHandler('pvip', precios_personalizados_command)
        ],
        states={
            MENU: [
                CallbackQueryHandler(menu_callback, pattern='^pp_'),
                CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            SELECCIONAR_CLIENTE: [
                CallbackQueryHandler(cliente_seleccionado, pattern='^cli_'),
                CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            SELECCIONAR_PRODUCTO: [
                CallbackQueryHandler(producto_seleccionado, pattern='^prod_'),
                CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$'),
                MessageHandler(filters.COMMAND, cancelar)
            ],
            INGRESAR_PRECIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_precio),
                MessageHandler(filters.COMMAND, cancelar)
            ]
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar),
            CallbackQueryHandler(precios_personalizados_command, pattern='^pp_volver$')
        ],
        conversation_timeout=300
    )
    
    application.add_handler(conv_handler)
    logger.info("Handlers de precios personalizados registrados correctamente")
