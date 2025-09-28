"""
Módulo para administrar el catálogo de WhatsApp desde Telegram
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
MENU, ACTUALIZAR_PRECIO, ACTUALIZAR_STOCK, EDITAR_INPUT = range(4)

logger = logging.getLogger(__name__)

async def catalogo_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Comando principal para administrar el catálogo"""
    
    keyboard = [
        [InlineKeyboardButton("📋 Ver catálogo actual", callback_data="cat_ver")],
        [InlineKeyboardButton("💰 Actualizar precio", callback_data="cat_precio")],
        [InlineKeyboardButton("📦 Actualizar stock", callback_data="cat_stock")],
        [InlineKeyboardButton("❌ Salir", callback_data="cat_salir")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    mensaje = """
*ADMINISTRACIÓN DE CATÁLOGO*
━━━━━━━━━━━━━━━━━━━━━

Selecciona una opción:

• *Ver catálogo*: Lista productos activos
• *Actualizar precio*: Cambiar precio de un producto
• *Actualizar stock*: Modificar cantidad disponible
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
    
    return MENU

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja las opciones del menú principal"""
    query = update.callback_query
    await query.answer()
    
    opcion = query.data.replace("cat_", "")
    
    if opcion == "salir":
        await query.edit_message_text("Administración de catálogo finalizada")
        return ConversationHandler.END
    
    elif opcion == "ver":
        await query.edit_message_text("Cargando catálogo...")
        
        # Obtener productos del catálogo
        productos = obtener_catalogo_productos()
        
        if not productos:
            keyboard = [[InlineKeyboardButton("Volver", callback_data="cat_volver")]]
            await query.edit_message_text(
                "No hay productos en el catálogo",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return MENU
        
        # Formatear lista de productos
        mensaje = "*CATÁLOGO ACTUAL*\n━━━━━━━━━━━━━━━━━━\n\n"
        
        for p in productos[:15]:  # Máximo 15 productos
            try:
                id_prod = p[0]
                nombre = p[1]
                precio = p[2]
                stock = p[6]
                estado = p[8]
                
                if estado == 'ACTIVO':
                    mensaje += f"*{nombre}*\n"
                    mensaje += f"ID: {id_prod}\n"
                    mensaje += f"Precio: S/{precio}/kg | Stock: {stock}kg\n"
                    mensaje += "─────────────\n"
                    
            except:
                continue
        
        keyboard = [[InlineKeyboardButton("Volver", callback_data="cat_volver")]]
        
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return MENU
    
    elif opcion == "volver":
        return await catalogo_admin_command(update, context)
    
    elif opcion == "precio":
        await query.edit_message_text(
            "*ACTUALIZAR PRECIO*\n\n"
            "Envía el ID del producto y el nuevo precio\n"
            "Formato: `ID PRECIO`\n\n"
            "Ejemplo: `CAT-001 35.50`\n\n"
            "_Escribe /cancelar para salir_",
            parse_mode='Markdown'
        )
        context.user_data['accion'] = 'precio'
        return EDITAR_INPUT
    
    elif opcion == "stock":
        await query.edit_message_text(
            "*ACTUALIZAR STOCK*\n\n"
            "Envía el ID del producto y el nuevo stock\n"
            "Formato: `ID CANTIDAD`\n\n"
            "Ejemplo: `CAT-001 150`\n\n"
            "_Escribe /cancelar para salir_",
            parse_mode='Markdown'
        )
        context.user_data['accion'] = 'stock'
        return EDITAR_INPUT

async def procesar_edicion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la actualización de precio o stock"""
    texto = update.message.text.strip()
    accion = context.user_data.get('accion')
    
    try:
        # Parsear entrada
        partes = texto.split()
        if len(partes) != 2:
            await update.message.reply_text(
                "Formato incorrecto. Usa: ID VALOR\n"
                "Ejemplo: CAT-001 35.50"
            )
            return EDITAR_INPUT
        
        id_producto = partes[0].upper()
        valor = partes[1]
        
        # Validar valor numérico
        try:
            valor_num = float(valor)
            if valor_num <= 0:
                await update.message.reply_text("El valor debe ser mayor a 0")
                return EDITAR_INPUT
        except ValueError:
            await update.message.reply_text("El valor debe ser un número")
            return EDITAR_INPUT
        
        await update.message.reply_text("Actualizando...")
        
        # Actualizar en Google Sheets
        exito = False
        if accion == 'precio':
            exito = actualizar_precio_producto(id_producto, valor_num)
            campo = "precio"
        elif accion == 'stock':
            exito = actualizar_stock_producto(id_producto, valor_num)
            campo = "stock"
        
        if exito:
            mensaje = f"✅ *{campo.upper()} ACTUALIZADO*\n\n"
            mensaje += f"Producto: {id_producto}\n"
            mensaje += f"Nuevo {campo}: {valor_num}"
            
            if accion == 'precio':
                mensaje += " soles/kg"
            else:
                mensaje += " kg"
            
            keyboard = [
                [InlineKeyboardButton("Ver catálogo", callback_data="cat_ver")],
                [InlineKeyboardButton("Menú principal", callback_data="cat_volver")]
            ]
            
            await update.message.reply_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Error al actualizar {campo}\n\n"
                f"Verifica que el ID {id_producto} existe"
            )
        
        return MENU
        
    except Exception as e:
        logger.error(f"Error procesando edición: {e}")
        await update.message.reply_text(
            "Error al procesar la actualización\n"
            "Intenta nuevamente"
        )
        return EDITAR_INPUT

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
        
        # Retornar solo productos con datos (skip header)
        return [row for row in values[1:] if len(row) > 0 and row[0]]
        
    except Exception as e:
        logger.error(f"Error obteniendo catálogo: {e}")
        return []

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
    await update.message.reply_text(
        "Operación cancelada\n\n"
        "Usa /catalogo_admin para volver a empezar"
    )
    return ConversationHandler.END

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
                MessageHandler(filters.COMMAND, cancelar)
            ],
            EDITAR_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_edicion),
                MessageHandler(filters.COMMAND, cancelar)
            ]
        },
        fallbacks=[
            CommandHandler('cancelar', cancelar)
        ]
    )
    
    application.add_handler(conv_handler)
    logger.info("Handlers de administración de catálogo registrados correctamente")