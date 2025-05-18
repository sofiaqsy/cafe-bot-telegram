import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler
)
from datetime import datetime

from utils.db import append_data, get_all_data
from utils.sheets import update_cell
from utils.helpers import format_currency, calculate_total, get_now_peru

# Estados para la conversación - actualizado para incluir tipo_cafe y quitar calidad
SELECCIONAR_PROVEEDOR, TIPO_CAFE, CANTIDAD, PRECIO, CONFIRMAR = range(5)

# Logger
logger = logging.getLogger(__name__)

# Estado pendiente para compras
ESTADO_PENDIENTE = "Pendiente"

# Tipos de café predefinidos - solo 3 opciones fijas (copiado de compras.py)
TIPOS_CAFE = ["CEREZO", "MOTE", "PERGAMINO"]

# Headers para la hoja de compras con adelanto - Se eliminó 'calidad' de la lista
COMPRAS_HEADERS = ["fecha", "hora", "tipo_cafe", "proveedor", "cantidad", "precio", "total", 
                   "monto_adelanto", "monto_efectivo", "kg_disponibles", "estado", "notas", "registrado_por"]

async def compra_con_adelanto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar proceso de registro de compra con adelanto"""
    try:
        logger.info(f"Usuario {update.effective_user.id} inició comando /compra_adelanto")
        
        # Limpiar datos previos
        context.user_data.clear()
        
        # Indicar que estamos en el flujo de compra con adelanto
        context.user_data['en_compra_adelanto'] = True
        
        # Obtener adelantos vigentes
        adelantos = get_all_data("adelantos")
        
        if not adelantos:
            await update.message.reply_text(
                "No hay adelantos registrados. "
                "Usa /compra para registrar una compra normal o /adelanto para registrar un adelanto."
            )
            return ConversationHandler.END
        
        # Filtrar adelantos con saldo
        adelantos_vigentes = []
        for adelanto in adelantos:
            try:
                saldo = float(adelanto.get('saldo_restante', 0))
                if saldo > 0:
                    adelantos_vigentes.append(adelanto)
            except (ValueError, TypeError):
                continue
        
        if not adelantos_vigentes:
            await update.message.reply_text(
                "No hay adelantos vigentes con saldo disponible. "
                "Usa /compra para registrar una compra normal o /adelanto para registrar un adelanto."
            )
            return ConversationHandler.END
        
        # Agrupar adelantos por proveedor para mostrar el saldo total
        proveedores = {}
        for adelanto in adelantos_vigentes:
            proveedor = adelanto.get('proveedor', '')
            saldo = float(adelanto.get('saldo_restante', 0))
            
            if proveedor in proveedores:
                proveedores[proveedor]['saldo'] += saldo
                proveedores[proveedor]['adelantos'].append(adelanto)
            else:
                proveedores[proveedor] = {
                    'saldo': saldo,
                    'adelantos': [adelanto]
                }
        
        # Crear teclado inline con proveedores
        keyboard = []
        for proveedor, datos in proveedores.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{proveedor} - {format_currency(datos['saldo'])}", 
                    callback_data=f"compra_proveedor_{proveedor}"
                )
            ])
        
        # Añadir botón de cancelar
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="compra_cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Guardar los datos de los proveedores para uso posterior
        context.user_data['proveedores'] = proveedores
        
        await update.message.reply_text(
            "🔄 COMPRA CON ADELANTO\n\n"
            "Este tipo de compra te permite utilizar el saldo de adelantos para pagar a proveedores.\n\n"
            "Selecciona el proveedor con adelanto disponible:", 
            reply_markup=reply_markup
        )
        return SELECCIONAR_PROVEEDOR
        
    except Exception as e:
        logger.error(f"Error iniciando compra con adelanto: {e}")
        await update.message.reply_text(
            "❌ Error al iniciar el proceso de compra con adelanto. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def seleccionar_proveedor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejar selección de proveedor con adelanto"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "compra_cancelar":
        await query.edit_message_text("❌ Operación cancelada.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Extraer nombre del proveedor del callback data
    proveedor = query.data.replace("compra_proveedor_", "")
    
    try:
        # Verificar que el proveedor existe en los datos guardados
        if 'proveedores' not in context.user_data or proveedor not in context.user_data['proveedores']:
            await query.edit_message_text(
                "❌ Error: Proveedor no encontrado. Por favor, inicia el proceso nuevamente."
            )
            return ConversationHandler.END
        
        # Obtener datos del proveedor
        datos_proveedor = context.user_data['proveedores'][proveedor]
        saldo_total = datos_proveedor['saldo']
        
        # Guardar datos necesarios
        context.user_data['proveedor'] = proveedor
        context.user_data['saldo_adelanto'] = saldo_total
        context.user_data['adelantos_proveedor'] = datos_proveedor['adelantos']
        
        # Crear teclado con las 3 opciones predefinidas para tipo de café
        keyboard = [[tipo] for tipo in TIPOS_CAFE]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Mostrar mensaje de proveedor seleccionado y solicitar tipo de café
        await query.edit_message_text(
            f"👨‍🌾 Proveedor seleccionado: {proveedor}\n"
            f"💰 Saldo disponible: {format_currency(saldo_total)}"
        )
        
        # Solicitar tipo de café con teclado
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Selecciona el tipo de café:",
            reply_markup=reply_markup
        )
        
        return TIPO_CAFE
    except Exception as e:
        logger.error(f"Error procesando selección de proveedor: {e}")
        await query.edit_message_text(
            "❌ Error al procesar la selección. Por favor, intenta nuevamente usando /compra_adelanto."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def tipo_cafe_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el tipo de café y solicitar la cantidad"""
    selected_tipo = update.message.text.strip().upper()
    
    # Verificar que sea uno de los tipos permitidos
    if selected_tipo not in TIPOS_CAFE:
        # Si no es un tipo válido, volver a mostrar las opciones
        keyboard = [[tipo] for tipo in TIPOS_CAFE]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Tipo de café no válido. Por favor, selecciona una de las opciones disponibles:",
            reply_markup=reply_markup
        )
        return TIPO_CAFE
    
    # Guardar el tipo de café
    context.user_data['tipo_cafe'] = selected_tipo
    logger.info(f"Usuario {update.effective_user.id} seleccionó tipo de café: {selected_tipo}")
    
    # Solicitar la cantidad de café
    await update.message.reply_text(
        f"Tipo de café: {selected_tipo}\n\n"
        "Ahora, ingresa la cantidad de café en kg:",
        reply_markup=ReplyKeyboardRemove()
    )
    return CANTIDAD

async def cantidad_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la cantidad y solicitar el precio"""
    try:
        cantidad_text = update.message.text.replace(',', '.').strip()
        cantidad = float(cantidad_text)
        
        if cantidad <= 0:
            await update.message.reply_text("⚠️ La cantidad debe ser mayor a cero. Intenta nuevamente:")
            return CANTIDAD
        
        context.user_data['cantidad'] = cantidad
        
        await update.message.reply_text(
            f"📦 Cantidad: {cantidad} kg\n\n"
            "¿Cuál es el precio por kilogramo?"
        )
        return PRECIO
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para la cantidad."
        )
        return CANTIDAD

async def precio_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el precio y mostrar resumen para confirmar"""
    try:
        precio_text = update.message.text.replace(',', '.').strip()
        precio = float(precio_text)
        
        if precio <= 0:
            await update.message.reply_text("⚠️ El precio debe ser mayor a cero. Intenta nuevamente:")
            return PRECIO
        
        context.user_data['precio'] = precio
        
        # Calcular total
        cantidad = context.user_data['cantidad']
        total = calculate_total(cantidad, precio)
        context.user_data['total'] = total
        
        # Obtener datos para el resumen
        proveedor = context.user_data['proveedor']
        tipo_cafe = context.user_data['tipo_cafe']
        saldo_adelanto = context.user_data['saldo_adelanto']
        
        # Calcular cuánto se pagará con adelanto y cuánto en efectivo
        if total <= saldo_adelanto:
            monto_adelanto = total
            monto_efectivo = 0
            nuevo_saldo = saldo_adelanto - total
        else:
            monto_adelanto = saldo_adelanto
            monto_efectivo = total - saldo_adelanto
            nuevo_saldo = 0
        
        context.user_data['monto_adelanto'] = monto_adelanto
        context.user_data['monto_efectivo'] = monto_efectivo
        context.user_data['nuevo_saldo'] = nuevo_saldo
        
        # Crear teclado para confirmación
        keyboard = [["Sí", "No"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Mostrar resumen para confirmar
        await update.message.reply_text(
            "📋 RESUMEN DE COMPRA CON ADELANTO\n\n"
            f"👨‍🌾 Proveedor: {proveedor}\n"
            f"☕ Tipo de café: {tipo_cafe}\n"
            f"📦 Cantidad: {context.user_data['cantidad']} kg\n"
            f"💵 Precio por kg: {format_currency(context.user_data['precio'])}\n"
            f"💰 Total: {format_currency(total)}\n\n"
            f"💳 Pago con adelanto: {format_currency(monto_adelanto)}\n"
            f"💵 Pago en efectivo: {format_currency(monto_efectivo)}\n"
            f"💰 Saldo restante: {format_currency(nuevo_saldo)}\n\n"
            "¿Confirmas esta compra?",
            reply_markup=reply_markup
        )
        return CONFIRMAR
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para el precio."
        )
        return PRECIO

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y registrar la compra con adelanto"""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si', 's', 'yes', 'y']:
        try:
            # Obtener datos para la compra
            proveedor = context.user_data['proveedor']
            tipo_cafe = context.user_data['tipo_cafe']
            cantidad = context.user_data['cantidad']
            precio = context.user_data['precio']
            total = context.user_data['total']
            monto_adelanto = context.user_data['monto_adelanto']
            monto_efectivo = context.user_data['monto_efectivo']
            nuevo_saldo = context.user_data['nuevo_saldo']
            
            # Actualizar saldos de adelantos en Google Sheets
            adelantos_proveedor = context.user_data['adelantos_proveedor']
            
            # Descontar el monto de los adelantos, empezando por los más antiguos
            monto_pendiente = monto_adelanto
            adelantos_actualizados = []
            
            # Ordenar adelantos por fecha (los más antiguos primero)
            adelantos_proveedor.sort(key=lambda x: x.get('fecha', ''))
            
            for adelanto in adelantos_proveedor:
                if monto_pendiente <= 0:
                    break
                
                try:
                    row_index = adelanto.get('_row_index')
                    saldo_actual = float(adelanto.get('saldo_restante', 0))
                    
                    if monto_pendiente >= saldo_actual:
                        # Consumir todo el adelanto
                        nuevo_saldo_adelanto = 0
                        monto_pendiente -= saldo_actual
                    else:
                        # Consumir parcialmente
                        nuevo_saldo_adelanto = saldo_actual - monto_pendiente
                        monto_pendiente = 0
                    
                    # Actualizar el saldo en Google Sheets
                    update_cell("adelantos", row_index, "saldo_restante", nuevo_saldo_adelanto)
                    adelantos_actualizados.append({
                        "proveedor": adelanto.get('proveedor'), 
                        "saldo_anterior": saldo_actual, 
                        "nuevo_saldo": nuevo_saldo_adelanto
                    })
                    
                except (ValueError, TypeError, KeyError) as e:
                    logger.error(f"Error al procesar adelanto: {e}")
                    continue
            
            # Registrar la compra
            now = get_now_peru()
            
            # Datos para la compra
            compra_data = {
                "fecha": now.strftime("%Y-%m-%d"),
                "hora": now.strftime("%H:%M:%S"),
                "tipo_cafe": tipo_cafe,
                "proveedor": proveedor,
                "cantidad": cantidad,
                "precio": precio,
                "total": total,
                "monto_adelanto": monto_adelanto,
                "monto_efectivo": monto_efectivo,
                "kg_disponibles": cantidad,  # Inicialmente, todo está disponible
                "estado": ESTADO_PENDIENTE,  # Estado inicial: Pendiente
                "notas": f"Compra con adelanto. Monto adelanto: {format_currency(monto_adelanto)}",
                "registrado_por": update.effective_user.username or update.effective_user.first_name
            }
            
            # Guardar la compra
            append_data("compras", compra_data, COMPRAS_HEADERS)
            
            # Confirmación al usuario (simplificada)
            await update.message.reply_text(
                "✅ Compra registrada correctamente:\n\n"
                f"👨‍🌾 Proveedor: {proveedor}\n"
                f"☕ Tipo de café: {tipo_cafe}\n"
                f"📦 Cantidad: {cantidad} kg\n"
                f"💵 Precio por kg: {format_currency(precio)}\n"
                f"💰 Total: {format_currency(total)}\n\n"
                f"💳 Pagado con adelanto: {format_currency(monto_adelanto)}\n"
                f"💵 Pagado en efectivo: {format_currency(monto_efectivo)}\n"
                f"💰 Nuevo saldo de adelanto: {format_currency(nuevo_saldo)}",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e:
            logger.error(f"Error al procesar compra con adelanto: {e}")
            await update.message.reply_text(
                "❌ Error al registrar la compra. Por favor, intenta nuevamente.",
                reply_markup=ReplyKeyboardRemove()
            )
    else:
        await update.message.reply_text(
            "❌ Compra cancelada",
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar la conversación"""
    await update.message.reply_text(
        "❌ Operación cancelada.",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END

def register_compra_adelanto_handlers(application):
    """Registrar handlers para compra con adelanto"""
    # Crear manejador de conversación
    compra_adelanto_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compra_adelanto", compra_con_adelanto_command)],
        states={
            SELECCIONAR_PROVEEDOR: [CallbackQueryHandler(seleccionar_proveedor_callback, pattern=r'^compra_proveedor_|^compra_cancelar$')],
            TIPO_CAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_cafe_step)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_step)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio_step)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        # Añadir opción para permitir que se caigan las conversaciones después de cierto tiempo de inactividad
        conversation_timeout=900  # 15 minutos - para evitar conversaciones colgadas
    )
    
    # Agregar el manejador a la aplicación
    application.add_handler(compra_adelanto_conv_handler)
    logger.info("Handlers de compra con adelanto registrados")