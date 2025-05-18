import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler
)
import traceback
from datetime import datetime

from utils.db import append_data, get_all_data
from utils.sheets import update_cell
from utils.helpers import format_currency, calculate_total, get_now_peru

# Estados para la conversación
SELECCIONAR_PROVEEDOR, CANTIDAD, PRECIO, CALIDAD, CONFIRMAR = range(5)

# Logger
logger = logging.getLogger(__name__)

# Estado pendiente para compras
ESTADO_PENDIENTE = "Pendiente"

# Headers para la hoja de compras con adelanto
COMPRAS_HEADERS = ["fecha", "hora", "proveedor", "cantidad", "precio", "calidad", "total", 
                   "monto_adelanto", "monto_efectivo", "kg_disponibles", "estado", "notas", "registrado_por"]

async def compra_con_adelanto_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Iniciar proceso de registro de compra con adelanto"""
    try:
        logger.info(f"Usuario {update.effective_user.id} inició comando /compra_adelanto")
        
        # Limpiar datos previos
        context.user_data.clear()
        
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
                    callback_data=f"sel_proveedor_{proveedor}"  # Cambiado para evitar conflictos
                )
            ])
        
        # Añadir botón de cancelar
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar_adelanto")])
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
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al iniciar el proceso de compra con adelanto. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def seleccionar_proveedor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejar selección de proveedor con adelanto"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancelar_adelanto":  # Cambiado para evitar conflictos
        await query.edit_message_text("❌ Operación cancelada.")
        return ConversationHandler.END
    
    # Extraer nombre del proveedor del callback data
    proveedor = query.data.replace("sel_proveedor_", "")  # Cambiado para evitar conflictos
    
    try:
        # Verificar que el proveedor existe en los datos guardados
        if 'proveedores' not in context.user_data or proveedor not in context.user_data['proveedores']:
            await query.edit_message_text(
                "❌ Error: Proveedor no encontrado. Por favor, inicia el proceso nuevamente con /compra_adelanto"
            )
            return ConversationHandler.END
        
        # Obtener datos del proveedor
        datos_proveedor = context.user_data['proveedores'][proveedor]
        saldo_total = datos_proveedor['saldo']
        
        # Guardar datos necesarios
        context.user_data['proveedor'] = proveedor
        context.user_data['saldo_adelanto'] = saldo_total
        context.user_data['adelantos_proveedor'] = datos_proveedor['adelantos']
        
        # Mostrar mensaje y continuar con el flujo normal de compra
        await query.edit_message_text(
            f"👨‍🌾 Proveedor seleccionado: {proveedor}\n"
            f"💰 Saldo disponible: {format_currency(saldo_total)}\n\n"
            f"Ahora, ¿cuántos kilogramos de café estás comprando?"
        )
        
        return CANTIDAD
    except Exception as e:
        logger.error(f"Error procesando selección de proveedor: {e}")
        logger.error(traceback.format_exc())
        await query.edit_message_text(
            "❌ Error al procesar la selección. Por favor, intenta nuevamente con /compra_adelanto"
        )
        return ConversationHandler.END

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
    except Exception as e:
        logger.error(f"Error en cantidad_step: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al procesar la cantidad. Por favor, intenta nuevamente con /compra_adelanto"
        )
        return ConversationHandler.END

async def precio_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el precio y solicitar la calidad"""
    try:
        precio_text = update.message.text.replace(',', '.').strip()
        precio = float(precio_text)
        
        if precio <= 0:
            await update.message.reply_text("⚠️ El precio debe ser mayor a cero. Intenta nuevamente:")
            return PRECIO
        
        context.user_data['precio'] = precio
        
        # Calcular total
        cantidad = context.user_data['cantidad']
        total = cantidad * precio  # Simplificado para evitar problemas
        context.user_data['total'] = total
        
        await update.message.reply_text(
            f"💵 Precio: {format_currency(precio)} por kg\n"
            f"💰 Total: {format_currency(total)}\n\n"
            "¿Cuál es la calidad del café (1-5 estrellas)?"
        )
        return CALIDAD
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para el precio."
        )
        return PRECIO
    except Exception as e:
        logger.error(f"Error en precio_step: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al procesar el precio. Por favor, intenta nuevamente con /compra_adelanto"
        )
        return ConversationHandler.END

async def calidad_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la calidad y mostrar resumen para confirmar"""
    try:
        calidad = int(update.message.text.strip())
        
        if not (1 <= calidad <= 5):
            await update.message.reply_text(
                "⚠️ La calidad debe ser un número del 1 al 5. Intenta nuevamente:"
            )
            return CALIDAD
        
        context.user_data['calidad'] = calidad
        
        # Verificar que los datos necesarios estén en el contexto
        required_keys = ['proveedor', 'saldo_adelanto', 'total', 'cantidad', 'precio']
        for key in required_keys:
            if key not in context.user_data:
                raise KeyError(f"Dato requerido no encontrado: {key}")
        
        # Obtener datos para el resumen
        proveedor = context.user_data['proveedor']
        saldo_adelanto = context.user_data['saldo_adelanto']
        total = context.user_data['total']
        
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
        
        # Mostrar estrellas para la calidad
        estrellas = '⭐' * calidad
        
        # Mostrar resumen para confirmar
        await update.message.reply_text(
            "📋 RESUMEN DE COMPRA CON ADELANTO\n\n"
            f"👨‍🌾 Proveedor: {proveedor}\n"
            f"📦 Cantidad: {context.user_data['cantidad']} kg\n"
            f"💵 Precio por kg: {format_currency(context.user_data['precio'])}\n"
            f"🏆 Calidad: {estrellas}\n"
            f"💰 Total: {format_currency(total)}\n\n"
            f"💳 Pago con adelanto: {format_currency(monto_adelanto)}\n"
            f"💵 Pago en efectivo: {format_currency(monto_efectivo)}\n"
            f"💰 Saldo restante: {format_currency(nuevo_saldo)}\n\n"
            "¿Confirmas esta compra? (Sí/No)"
        )
        return CONFIRMAR
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número del 1 al 5 para la calidad."
        )
        return CALIDAD
    except Exception as e:
        logger.error(f"Error en calidad_step: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al procesar la calidad. Por favor, intenta nuevamente con /compra_adelanto"
        )
        return ConversationHandler.END

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y registrar la compra con adelanto"""
    respuesta = update.message.text.lower()
    
    if respuesta in ['sí', 'si', 's', 'yes', 'y']:
        try:
            # Verificar que los datos necesarios estén en el contexto
            required_keys = ['proveedor', 'cantidad', 'precio', 'calidad', 'total', 
                            'monto_adelanto', 'monto_efectivo', 'adelantos_proveedor']
            for key in required_keys:
                if key not in context.user_data:
                    raise KeyError(f"Dato requerido no encontrado: {key}")
            
            # Obtener datos para la compra
            proveedor = context.user_data['proveedor']
            cantidad = context.user_data['cantidad']
            precio = context.user_data['precio']
            calidad = context.user_data['calidad']
            total = context.user_data['total']
            monto_adelanto = context.user_data['monto_adelanto']
            monto_efectivo = context.user_data['monto_efectivo']
            nuevo_saldo = context.user_data.get('nuevo_saldo', 0)
            
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
                    if row_index is None:
                        logger.warning(f"Adelanto sin índice de fila: {adelanto}")
                        continue
                        
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
                    logger.info(f"Actualizando saldo de adelanto {row_index} de {saldo_actual} a {nuevo_saldo_adelanto}")
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
                "proveedor": proveedor,
                "cantidad": cantidad,
                "precio": precio,
                "calidad": calidad,
                "total": total,
                "monto_adelanto": monto_adelanto,
                "monto_efectivo": monto_efectivo,
                "kg_disponibles": cantidad,  # Inicialmente, todo está disponible
                "estado": ESTADO_PENDIENTE,  # Estado inicial: Pendiente
                "notas": f"Compra con adelanto. Monto adelanto: {format_currency(monto_adelanto)}",
                "registrado_por": update.effective_user.username or update.effective_user.first_name
            }
            
            # Guardar la compra
            logger.info(f"Guardando compra: {compra_data}")
            append_data("compras", compra_data, COMPRAS_HEADERS)
            
            # Mostrar estrellas para la calidad
            estrellas = '⭐' * calidad
            
            # Detalles de los adelantos actualizados
            adelantos_text = ""
            for a in adelantos_actualizados:
                adelantos_text += f"  - {a['proveedor']}: {format_currency(a['saldo_anterior'])} → {format_currency(a['nuevo_saldo'])}\n"
            
            # Confirmación al usuario
            await update.message.reply_text(
                "✅ Compra registrada correctamente:\n\n"
                f"👨‍🌾 Proveedor: {proveedor}\n"
                f"📦 Cantidad: {cantidad} kg\n"
                f"💵 Precio por kg: {format_currency(precio)}\n"
                f"🏆 Calidad: {estrellas}\n"
                f"💰 Total: {format_currency(total)}\n\n"
                f"💳 Pagado con adelanto: {format_currency(monto_adelanto)}\n"
                f"💵 Pagado en efectivo: {format_currency(monto_efectivo)}\n"
                f"💰 Nuevo saldo de adelanto: {format_currency(nuevo_saldo)}\n\n"
                f"Adelantos actualizados:\n{adelantos_text}"
            )
        except Exception as e:
            logger.error(f"Error al procesar compra con adelanto: {e}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                "❌ Error al registrar la compra. Por favor, intenta nuevamente con /compra_adelanto"
            )
    else:
        await update.message.reply_text("❌ Compra cancelada")
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar la conversación"""
    await update.message.reply_text(
        "❌ Operación cancelada."
    )
    context.user_data.clear()
    return ConversationHandler.END

def register_compra_adelanto_handlers(application):
    """Registrar handlers para compra con adelanto"""
    # Crear manejador de conversación
    compra_adelanto_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compra_adelanto", compra_con_adelanto_command)],
        states={
            SELECCIONAR_PROVEEDOR: [
                CallbackQueryHandler(seleccionar_proveedor_callback, pattern=r'^sel_proveedor_|^cancelar_adelanto$')
            ],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_step)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio_step)],
            CALIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, calidad_step)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador a la aplicación
    application.add_handler(compra_adelanto_conv_handler)
    logger.info("Handlers de compra con adelanto registrados")