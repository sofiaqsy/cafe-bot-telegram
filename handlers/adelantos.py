import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from datetime import datetime
import traceback

# Importar módulos para Google Sheets
from utils.db import append_data, get_all_data
from utils.helpers import format_currency, get_now_peru
from utils.sheets import update_cell

# Estados para la conversación
PROVEEDOR, MONTO, NOTAS, CONFIRMAR = range(4)

# Logger
logger = logging.getLogger(__name__)

# Headers para la hoja de adelantos
ADELANTOS_HEADERS = ["fecha", "hora", "proveedor", "monto", "saldo_restante", "notas", "registrado_por"]

# Función para obtener fecha y hora actuales
def get_now():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

# Funciones para el manejo de adelantos
async def adelanto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar el proceso de registro de adelanto"""
    await update.message.reply_text(
        "📝 Registro de adelanto a proveedor\n\n"
        "Los adelantos son pagos anticipados a proveedores que se descontarán de futuras compras.\n\n"
        "Por favor, ingresa el nombre del proveedor:"
    )
    return PROVEEDOR

async def proveedor_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir nombre del proveedor"""
    context.user_data['proveedor'] = update.message.text.strip()
    
    # Verificar si ya tiene adelantos vigentes
    try:
        adelantos = get_all_data("adelantos")
        
        # Filtrar adelantos del proveedor con saldo
        adelantos_proveedor = []
        for adelanto in adelantos:
            if adelanto.get('proveedor') == context.user_data['proveedor']:
                try:
                    saldo = float(adelanto.get('saldo_restante', 0))
                    if saldo > 0:
                        adelantos_proveedor.append(adelanto)
                except (ValueError, TypeError):
                    continue
        
        # Calcular saldo total
        if adelantos_proveedor:
            saldo_total = sum(float(adelanto.get('saldo_restante', 0)) for adelanto in adelantos_proveedor)
            await update.message.reply_text(
                f"ℹ️ El proveedor {context.user_data['proveedor']} ya tiene adelantos vigentes "
                f"por un total de {format_currency(saldo_total)}.\n\n"
                "Este nuevo adelanto se sumará al saldo existente."
            )
    except Exception as e:
        logger.error(f"Error al verificar adelantos del proveedor: {e}")
    
    await update.message.reply_text(
        "💸 ¿Cuál es el monto del adelanto? (en S/)"
    )
    return MONTO

async def monto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir monto del adelanto"""
    try:
        monto_text = update.message.text.replace(',', '.').strip()
        monto = float(monto_text)
        
        if monto <= 0:
            await update.message.reply_text("⚠️ El monto debe ser mayor a cero. Intenta de nuevo:")
            return MONTO
        
        context.user_data['monto'] = monto
        context.user_data['saldo_restante'] = monto
        
        await update.message.reply_text(
            "📝 Opcionalmente, puedes agregar notas o detalles sobre este adelanto:\n"
            "(Envía '-' si no deseas agregar notas)"
        )
        return NOTAS
    except ValueError:
        await update.message.reply_text(
            "⚠️ El valor ingresado no es válido. Por favor, ingresa solo números:"
        )
        return MONTO

async def notas_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir notas adicionales"""
    if update.message.text.strip() == '-':
        context.user_data['notas'] = ''
    else:
        context.user_data['notas'] = update.message.text.strip()
    
    # Mostrar resumen para confirmar
    await update.message.reply_text(
        f"📋 RESUMEN DEL ADELANTO\n\n"
        f"Proveedor: {context.user_data['proveedor']}\n"
        f"Monto: {format_currency(context.user_data['monto'])}\n"
        f"Saldo restante: {format_currency(context.user_data['saldo_restante'])}\n"
        f"Notas: {context.user_data['notas'] or 'N/A'}\n\n"
        f"¿Confirmas este adelanto? (Sí/No)"
    )
    return CONFIRMAR

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y guardar el adelanto"""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si', 's', 'yes', 'y']:
        # Guardar el adelanto
        fecha, hora = get_now()
        
        data = {
            "fecha": fecha,
            "hora": hora,
            "proveedor": context.user_data['proveedor'],
            "monto": context.user_data['monto'],
            "saldo_restante": context.user_data['saldo_restante'],
            "notas": context.user_data['notas'],
            "registrado_por": update.effective_user.username or update.effective_user.first_name
        }
        
        try:
            # Guardar el adelanto usando la función append_data
            append_data("adelantos", data, ADELANTOS_HEADERS)
            
            await update.message.reply_text(
                f"✅ Adelanto registrado correctamente\n\n"
                f"Se ha registrado un adelanto de {format_currency(context.user_data['monto'])} "
                f"para el proveedor {context.user_data['proveedor']}.\n\n"
                f"Este monto se descontará automáticamente de futuras compras a este proveedor.\n\n"
                f"Usa /compra_adelanto para registrar una compra con este adelanto."
            )
        except Exception as e:
            logger.error(f"Error guardando adelanto: {e}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                "❌ Error al registrar el adelanto. Por favor, intenta nuevamente."
            )
    else:
        await update.message.reply_text("❌ Registro cancelado")
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar_adelanto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar el registro de adelanto"""
    await update.message.reply_text(
        "❌ Registro de adelanto cancelado",
        reply_markup=None
    )
    context.user_data.clear()
    return ConversationHandler.END

async def lista_adelantos_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar lista de adelantos vigentes con opciones interactivas"""
    # Verificar si estamos manejando una actualización de mensaje o un callback
    is_callback = update.callback_query is not None
    
    try:
        # Obtener adelantos desde Google Sheets
        adelantos = get_all_data("adelantos")
        
        # Verificar si hay adelantos
        if not adelantos:
            if is_callback:
                await update.callback_query.edit_message_text("No hay adelantos registrados.")
            else:
                await update.message.reply_text("No hay adelantos registrados.")
            return
        
        # Filtrar adelantos con saldo positivo
        adelantos_vigentes = []
        for adelanto in adelantos:
            try:
                saldo = float(adelanto.get('saldo_restante', 0))
                if saldo > 0:
                    adelantos_vigentes.append(adelanto)
            except (ValueError, TypeError):
                continue
        
        # Verificar si hay adelantos vigentes
        if not adelantos_vigentes:
            if is_callback:
                await update.callback_query.edit_message_text("No hay adelantos vigentes con saldo disponible.")
            else:
                await update.message.reply_text("No hay adelantos vigentes con saldo disponible.")
            return
        
        # Agrupar adelantos por proveedor
        proveedores = {}
        for adelanto in adelantos_vigentes:
            proveedor = adelanto.get('proveedor', '')
            monto = float(adelanto.get('monto', 0))
            saldo = float(adelanto.get('saldo_restante', 0))
            fecha = adelanto.get('fecha', '')
            row_index = adelanto.get('_row_index')
            
            if proveedor not in proveedores:
                proveedores[proveedor] = {
                    'adelantos': [],
                    'total_monto': 0,
                    'total_saldo': 0
                }
            
            proveedores[proveedor]['adelantos'].append({
                'fecha': fecha,
                'monto': monto,
                'saldo': saldo,
                'row_index': row_index
            })
            proveedores[proveedor]['total_monto'] += monto
            proveedores[proveedor]['total_saldo'] += saldo
        
        # Crear mensaje con los adelantos agrupados
        mensaje = "💰 ADELANTOS VIGENTES:\n\n"
        
        # Crear botones para filtrar por proveedor
        keyboard = []
        
        for proveedor, datos in proveedores.items():
            keyboard.append([InlineKeyboardButton(
                f"{proveedor} - {format_currency(datos['total_saldo'])}", 
                callback_data=f"proveedor_{proveedor}"
            )])
            
            mensaje += f"👨‍🌾 Proveedor: {proveedor}\n"
            mensaje += f"💵 Total adelantado: {format_currency(datos['total_monto'])}\n"
            mensaje += f"💰 Saldo disponible: {format_currency(datos['total_saldo'])}\n"
            mensaje += "\n"
        
        # Añadir instrucciones para usar adelantos
        mensaje += "Para usar estos adelantos en una compra, utiliza el comando /compra_adelanto.\n"
        
        # Crear teclado inline para botones
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Enviar mensaje (limitar a 4000 caracteres si es necesario)
        if len(mensaje) > 4000:
            mensaje = mensaje[:3950] + "...\n\n(Mensaje truncado debido a su longitud)"
        
        # Enviar mensaje según el tipo de actualización
        if is_callback:
            await update.callback_query.edit_message_text(mensaje, reply_markup=reply_markup)
        else:
            await update.message.reply_text(mensaje, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error obteniendo adelantos: {e}")
        logger.error(traceback.format_exc())
        try:
            if is_callback:
                await update.callback_query.edit_message_text(f"Error al obtener los adelantos: {str(e)}")
            else:
                await update.message.reply_text(f"Error al obtener los adelantos: {str(e)}")
        except Exception as e2:
            logger.error(f"Error secundario al manejar el error original: {e2}")

async def proveedor_adelantos_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mostrar los adelantos de un proveedor específico"""
    query = update.callback_query
    await query.answer()
    
    # Ignorar los callbacks relacionados con compra_adelanto
    if query.data.startswith("compra_proveedor_") or query.data == "compra_cancelar":
        # Estos son manejados por el ConversationHandler de compra_adelanto.py
        return
    
    if query.data == "ver_todos":
        try:
            # Cuando queremos volver a mostrar todos los adelantos
            await lista_adelantos_command(update, context)
            return
        except Exception as e:
            logger.error(f"Error al mostrar todos los adelantos: {e}")
            await query.edit_message_text("Error al mostrar todos los adelantos. Intenta con /adelantos")
            return
    
    # Si es un comando para iniciar una compra con adelanto, pasamos directamente al proceso de compra
    if query.data.startswith("compra_adelanto_"):
        proveedor = query.data.replace("compra_adelanto_", "")
        # Aquí iría el código para iniciar el proceso de compra con adelanto
        # Por ahora solo mostramos un mensaje informativo
        await query.edit_message_text(
            f"Iniciando compra con adelanto para el proveedor {proveedor}..."
        )
        return
        
    # Extraer nombre del proveedor del callback_data
    proveedor = query.data.replace("proveedor_", "")
    
    try:
        # Obtener adelantos del proveedor
        adelantos = get_all_data("adelantos")
        
        # Filtrar adelantos del proveedor con saldo positivo
        adelantos_proveedor = []
        for adelanto in adelantos:
            if adelanto.get('proveedor') == proveedor:
                try:
                    saldo = float(adelanto.get('saldo_restante', 0))
                    if saldo > 0:
                        adelantos_proveedor.append(adelanto)
                except (ValueError, TypeError):
                    continue
        
        if not adelantos_proveedor:
            await query.edit_message_text(
                f"No hay adelantos vigentes para el proveedor {proveedor}."
            )
            return
        
        # Calcular totales
        total_monto = sum(float(adelanto.get('monto', 0)) for adelanto in adelantos_proveedor)
        total_saldo = sum(float(adelanto.get('saldo_restante', 0)) for adelanto in adelantos_proveedor)
        
        # Crear mensaje simplificado
        mensaje = f"📋 ADELANTOS DE {proveedor.upper()}\n\n"
        mensaje += f"💵 Total adelantado: {format_currency(total_monto)}\n"
        mensaje += f"💰 Saldo disponible: {format_currency(total_saldo)}\n\n"
        
        # Botones para navegar y acciones
        keyboard = []
        keyboard.append([InlineKeyboardButton("⬅️ Volver a todos los proveedores", callback_data="ver_todos")])
        
        # Enviar mensaje con teclado inline
        await query.edit_message_text(
            mensaje,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error al mostrar adelantos del proveedor: {e}")
        logger.error(traceback.format_exc())
        await query.edit_message_text(
            f"Error al obtener los adelantos: {str(e)}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Volver", callback_data="ver_todos")]
            ])
        )

def register_adelantos_handlers(application):
    """Registrar handlers para adelantos"""
    logger.info("Registrando handlers de adelantos")
    
    # Registro de adelantos
    adelanto_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("adelanto", adelanto_command)],
        states={
            PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor_step)],
            MONTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_step)],
            NOTAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, notas_step)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar_adelanto)],
    )
    
    # Listar adelantos
    application.add_handler(CommandHandler("adelantos", lista_adelantos_command))
    
    # Callbacks para manejar interacciones con los botones
    # Modificado para ignorar los callbacks de compra_adelanto
    application.add_handler(CallbackQueryHandler(proveedor_adelantos_callback, pattern=r'^proveedor_|^ver_todos$|^compra_adelanto_'))
    
    application.add_handler(adelanto_conv_handler)
    
    logger.info("Handlers de adelantos registrados correctamente")