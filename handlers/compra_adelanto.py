import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler
)
from datetime import datetime
import traceback

from utils.db import append_data, get_all_data
from utils.sheets import update_cell
from utils.helpers import format_currency, calculate_total, get_now_peru

# Estados para la conversación
SELECCIONAR_PROVEEDOR, CANTIDAD, PRECIO, CALIDAD, CONFIRMAR = range(5)

# Estado para la selección de adelanto específico
SELECCIONAR_ADELANTO = 5

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
        
        # Agrupar adelantos por proveedor
        proveedores = {}
        for adelanto in adelantos_vigentes:
            proveedor = adelanto.get('proveedor', '')
            saldo = float(adelanto.get('saldo_restante', 0))
            fecha = adelanto.get('fecha', '')
            row_index = adelanto.get('_row_index')
            
            if proveedor in proveedores:
                proveedores[proveedor]['saldo_total'] += saldo
                proveedores[proveedor]['adelantos'].append({
                    'fecha': fecha,
                    'saldo': saldo,
                    'row_index': row_index
                })
            else:
                proveedores[proveedor] = {
                    'saldo_total': saldo,
                    'adelantos': [{
                        'fecha': fecha,
                        'saldo': saldo,
                        'row_index': row_index
                    }]
                }
        
        # Guardar los datos de los proveedores para uso posterior
        context.user_data['proveedores'] = proveedores
        
        # Crear teclado inline con proveedores
        keyboard = []
        for proveedor, datos in proveedores.items():
            keyboard.append([
                InlineKeyboardButton(
                    f"{proveedor} - Saldo: {format_currency(datos['saldo_total'])}", 
                    callback_data=f"proveedor_{proveedor}"
                )
            ])
        
        # Añadir botón de cancelar
        keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔄 COMPRA CON ADELANTO\n\n"
            "Selecciona un proveedor con adelanto disponible para realizar una compra:\n\n"
            "El saldo de adelanto se descontará automáticamente del monto total de la compra.", 
            reply_markup=reply_markup
        )
        return SELECCIONAR_PROVEEDOR
        
    except Exception as e:
        logger.error(f"Error iniciando compra con adelanto: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al iniciar el proceso de compra con adelanto. Por favor, intenta nuevamente con /compra_adelanto."
        )
        # Asegurar que limpiamos los datos y terminamos la conversación
        context.user_data.clear()
        return ConversationHandler.END

async def seleccionar_proveedor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejar selección de proveedor con adelanto"""
    query = update.callback_query
    try:
        await query.answer()
        
        if query.data == "cancelar":
            await query.edit_message_text("❌ Operación cancelada.")
            context.user_data.clear()
            return ConversationHandler.END
        
        # Extraer nombre del proveedor del callback data
        proveedor = query.data.replace("proveedor_", "")
        
        # Verificar que el proveedor existe en los datos guardados
        if 'proveedores' not in context.user_data:
            await query.edit_message_text(
                "❌ Error: Datos de la conversación perdidos. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
            context.user_data.clear()
            return ConversationHandler.END
            
        if proveedor not in context.user_data['proveedores']:
            await query.edit_message_text(
                "❌ Error: Proveedor no encontrado. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        # Obtener datos del proveedor
        datos_proveedor = context.user_data['proveedores'][proveedor]
        
        # Si el proveedor tiene más de un adelanto, mostrar lista detallada
        if len(datos_proveedor['adelantos']) > 1:
            # Crear mensaje para mostrar los adelantos disponibles
            mensaje = f"📋 ADELANTOS DE {proveedor.upper()}\n\n"
            mensaje += f"💰 Saldo total disponible: {format_currency(datos_proveedor['saldo_total'])}\n\n"
            mensaje += "Selecciona un adelanto específico o usa el saldo total:\n"
            
            # Crear teclado con opciones para cada adelanto
            keyboard = []
            
            # Añadir opción para usar el saldo total
            keyboard.append([
                InlineKeyboardButton(
                    f"📊 Usar saldo total: {format_currency(datos_proveedor['saldo_total'])}",
                    callback_data=f"saldo_total_{proveedor}"
                )
            ])
            
            # Añadir opción para cada adelanto individual
            for i, adelanto in enumerate(datos_proveedor['adelantos']):
                keyboard.append([
                    InlineKeyboardButton(
                        f"💸 {adelanto['fecha']}: {format_currency(adelanto['saldo'])}",
                        callback_data=f"adelanto_{proveedor}_{adelanto['row_index']}"
                    )
                ])
            
            # Añadir botón para volver
            keyboard.append([InlineKeyboardButton("⬅️ Volver", callback_data="volver")])
            keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")])
            
            # Mostrar mensaje con opciones
            await query.edit_message_text(
                mensaje,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SELECCIONAR_ADELANTO
        else:
            # Si solo hay un adelanto, seleccionarlo directamente
            adelanto = datos_proveedor['adelantos'][0]
            saldo = adelanto['saldo']
            row_index = adelanto['row_index']
            
            # Guardar datos necesarios
            context.user_data['proveedor'] = proveedor
            context.user_data['saldo_adelanto'] = saldo
            context.user_data['adelantos_seleccionados'] = [row_index]
            
            # Continuar con el flujo de compra
            await query.edit_message_text(
                f"👨‍🌾 Proveedor seleccionado: {proveedor}\n"
                f"💰 Saldo disponible: {format_currency(saldo)}\n\n"
                f"Ahora, ¿cuántos kilogramos de café estás comprando?\n\n"
                f"(Para cancelar en cualquier momento, usa /cancelar)"
            )
            
            return CANTIDAD
        
    except Exception as e:
        logger.error(f"Error procesando selección de proveedor: {e}")
        logger.error(traceback.format_exc())
        try:
            await query.edit_message_text(
                "❌ Error al procesar la selección. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
        except Exception:
            # Si no podemos editar el mensaje, intentamos enviar uno nuevo
            try:
                await update.effective_chat.send_message(
                    "❌ Error al procesar la selección. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
            except Exception as e2:
                logger.error(f"Error secundario al enviar mensaje: {e2}")
        
        context.user_data.clear()
        return ConversationHandler.END

async def seleccionar_adelanto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manejar selección de adelanto específico"""
    query = update.callback_query
    try:
        await query.answer()
        
        if query.data == "cancelar":
            await query.edit_message_text("❌ Operación cancelada.")
            context.user_data.clear()
            return ConversationHandler.END
            
        if query.data == "volver":
            # Volver a la selección de proveedor
            return await compra_con_adelanto_command(update, context)
        
        if 'proveedores' not in context.user_data:
            await query.edit_message_text(
                "❌ Error: Datos de la conversación perdidos. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
        if query.data.startswith("saldo_total_"):
            # Usuario eligió usar el saldo total del proveedor
            proveedor = query.data.replace("saldo_total_", "")
            
            if proveedor not in context.user_data['proveedores']:
                await query.edit_message_text(
                    "❌ Error: Proveedor no encontrado. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
                context.user_data.clear()
                return ConversationHandler.END
                
            datos_proveedor = context.user_data['proveedores'][proveedor]
            
            # Obtener todos los row_index de los adelantos del proveedor
            adelantos_rows = [a['row_index'] for a in datos_proveedor['adelantos']]
            
            # Guardar datos
            context.user_data['proveedor'] = proveedor
            context.user_data['saldo_adelanto'] = datos_proveedor['saldo_total']
            context.user_data['adelantos_seleccionados'] = adelantos_rows
            
            await query.edit_message_text(
                f"👨‍🌾 Proveedor seleccionado: {proveedor}\n"
                f"💰 Saldo total disponible: {format_currency(datos_proveedor['saldo_total'])}\n\n"
                f"Ahora, ¿cuántos kilogramos de café estás comprando?\n\n"
                f"(Para cancelar en cualquier momento, usa /cancelar)"
            )
            
            return CANTIDAD
            
        elif query.data.startswith("adelanto_"):
            # Usuario eligió un adelanto específico
            _, proveedor, row_index = query.data.split("_", 2)
            
            if proveedor not in context.user_data['proveedores']:
                await query.edit_message_text(
                    "❌ Error: Proveedor no encontrado. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
                context.user_data.clear()
                return ConversationHandler.END
                
            try:
                row_index = int(row_index)
            except ValueError:
                await query.edit_message_text(
                    "❌ Error en el identificador del adelanto. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
                context.user_data.clear()
                return ConversationHandler.END
            
            # Buscar el adelanto seleccionado
            adelanto_seleccionado = None
            for adelanto in context.user_data['proveedores'][proveedor]['adelantos']:
                if adelanto['row_index'] == row_index:
                    adelanto_seleccionado = adelanto
                    break
            
            if not adelanto_seleccionado:
                await query.edit_message_text(
                    "❌ Error: No se encontró el adelanto seleccionado. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
                context.user_data.clear()
                return ConversationHandler.END
            
            # Guardar datos
            context.user_data['proveedor'] = proveedor
            context.user_data['saldo_adelanto'] = adelanto_seleccionado['saldo']
            context.user_data['adelantos_seleccionados'] = [row_index]
            
            await query.edit_message_text(
                f"👨‍🌾 Proveedor seleccionado: {proveedor}\n"
                f"💰 Adelanto seleccionado: {format_currency(adelanto_seleccionado['saldo'])} "
                f"(Fecha: {adelanto_seleccionado['fecha']})\n\n"
                f"Ahora, ¿cuántos kilogramos de café estás comprando?\n\n"
                f"(Para cancelar en cualquier momento, usa /cancelar)"
            )
            
            return CANTIDAD
        
        else:
            # Opción no reconocida
            await query.edit_message_text(
                "❌ Error: Opción no válida. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
            context.user_data.clear()
            return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error procesando selección de adelanto: {e}")
        logger.error(traceback.format_exc())
        try:
            await query.edit_message_text(
                "❌ Error al procesar la selección. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
        except Exception:
            # Si no podemos editar el mensaje, intentamos enviar uno nuevo
            try:
                await update.effective_chat.send_message(
                    "❌ Error al procesar la selección. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
            except Exception as e2:
                logger.error(f"Error secundario al enviar mensaje: {e2}")
        
        context.user_data.clear()
        return ConversationHandler.END

async def cantidad_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la cantidad y solicitar el precio"""
    try:
        # Verificar que tenemos los datos necesarios
        if 'proveedor' not in context.user_data or 'saldo_adelanto' not in context.user_data:
            await update.message.reply_text(
                "❌ Error: Datos de la conversación perdidos. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
            context.user_data.clear()
            return ConversationHandler.END
            
        cantidad_text = update.message.text.replace(',', '.').strip()
        cantidad = float(cantidad_text)
        
        if cantidad <= 0:
            await update.message.reply_text("⚠️ La cantidad debe ser mayor a cero. Intenta nuevamente:")
            return CANTIDAD
        
        context.user_data['cantidad'] = cantidad
        
        await update.message.reply_text(
            f"📦 Cantidad: {cantidad} kg\n\n"
            "¿Cuál es el precio por kilogramo? (en S/)\n\n"
            "(Para cancelar en cualquier momento, usa /cancelar)"
        )
        return PRECIO
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para la cantidad. Sólo números (ej: 12.5)."
        )
        return CANTIDAD
    except Exception as e:
        logger.error(f"Error en paso de cantidad: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al procesar la cantidad. Por favor, inicia el proceso nuevamente con /compra_adelanto."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def precio_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el precio y solicitar la calidad"""
    try:
        # Verificar que tenemos los datos necesarios
        if 'proveedor' not in context.user_data or 'cantidad' not in context.user_data:
            await update.message.reply_text(
                "❌ Error: Datos de la conversación perdidos. Por favor, inicia el proceso nuevamente con /compra_adelanto."
            )
            context.user_data.clear()
            return ConversationHandler.END
            
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
        
        await update.message.reply_text(
            f"💵 Precio: {format_currency(precio)} por kg\n"
            f"💰 Total: {format_currency(total)}\n\n"
            "¿Cuál es la calidad del café (1-5 estrellas)?\n\n"
            "(Para cancelar en cualquier momento, usa /cancelar)"
        )
        return CALIDAD
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número válido para el precio. Sólo números (ej: 15.50)."
        )
        return PRECIO
    except Exception as e:
        logger.error(f"Error en paso de precio: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al procesar el precio. Por favor, inicia el proceso nuevamente con /compra_adelanto."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def calidad_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la calidad y mostrar resumen para confirmar"""
    try:
        # Verificar que tenemos los datos necesarios
        required_fields = ['proveedor', 'cantidad', 'precio', 'total', 'saldo_adelanto']
        for field in required_fields:
            if field not in context.user_data:
                await update.message.reply_text(
                    "❌ Error: Datos de la conversación perdidos. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
                context.user_data.clear()
                return ConversationHandler.END
        
        calidad = int(update.message.text.strip())
        
        if not (1 <= calidad <= 5):
            await update.message.reply_text(
                "⚠️ La calidad debe ser un número del 1 al 5. Intenta nuevamente:"
            )
            return CALIDAD
        
        context.user_data['calidad'] = calidad
        
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
            "\u00bfConfirmas esta compra? (Sí/No)\n\n"
            "(Para cancelar, responde 'No' o usa /cancelar)"
        )
        return CONFIRMAR
    except ValueError:
        await update.message.reply_text(
            "⚠️ Por favor, ingresa un número del 1 al 5 para la calidad."
        )
        return CALIDAD
    except Exception as e:
        logger.error(f"Error en paso de calidad: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al procesar la calidad. Por favor, inicia el proceso nuevamente con /compra_adelanto."
        )
        context.user_data.clear()
        return ConversationHandler.END

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y registrar la compra con adelanto"""
    try:
        # Verificar que tenemos todos los datos necesarios
        required_fields = ['proveedor', 'cantidad', 'precio', 'calidad', 'total', 
                          'monto_adelanto', 'monto_efectivo', 'adelantos_seleccionados']
        for field in required_fields:
            if field not in context.user_data:
                await update.message.reply_text(
                    "❌ Error: Datos de la conversación perdidos. Por favor, inicia el proceso nuevamente con /compra_adelanto."
                )
                context.user_data.clear()
                return ConversationHandler.END
                
        respuesta = update.message.text.lower()
        
        if respuesta in ['sí', 'si', 's', 'yes', 'y']:
            # Obtener datos para la compra
            proveedor = context.user_data['proveedor']
            cantidad = context.user_data['cantidad']
            precio = context.user_data['precio']
            calidad = context.user_data['calidad']
            total = context.user_data['total']
            monto_adelanto = context.user_data['monto_adelanto']
            monto_efectivo = context.user_data['monto_efectivo']
            nuevo_saldo = context.user_data.get('nuevo_saldo', 0)
            adelantos_seleccionados = context.user_data['adelantos_seleccionados']
            
            # Obtener todos los adelantos para procesar los seleccionados
            adelantos = get_all_data("adelantos")
            
            # Descontar el monto de los adelantos seleccionados
            monto_pendiente = monto_adelanto
            adelantos_actualizados = []
            
            # Si hay múltiples adelantos, procesarlos en orden (más antiguos primero)
            adelantos_a_procesar = []
            for row_index in adelantos_seleccionados:
                for adelanto in adelantos:
                    if adelanto.get('_row_index') == row_index:
                        adelantos_a_procesar.append(adelanto)
                        break
            
            # Ordenar por fecha (más antiguos primero)
            adelantos_a_procesar.sort(key=lambda x: x.get('fecha', ''))
            
            # Procesar cada adelanto hasta completar el monto
            for adelanto in adelantos_a_procesar:
                if monto_pendiente <= 0:
                    break
                
                try:
                    row_index = adelanto.get('_row_index')
                    saldo_actual = float(adelanto.get('saldo_restante', 0))
                    
                    if monto_pendiente >= saldo_actual:
                        # Consumir todo el adelanto
                        nuevo_saldo_adelanto = 0
                        monto_usado = saldo_actual
                        monto_pendiente -= saldo_actual
                    else:
                        # Consumir parcialmente
                        nuevo_saldo_adelanto = saldo_actual - monto_pendiente
                        monto_usado = monto_pendiente
                        monto_pendiente = 0
                    
                    # Actualizar el saldo en Google Sheets
                    update_cell("adelantos", row_index, "saldo_restante", nuevo_saldo_adelanto)
                    
                    # Guardar para mostrar en la confirmación
                    adelantos_actualizados.append({
                        "proveedor": adelanto.get('proveedor'), 
                        "fecha": adelanto.get('fecha', ''),
                        "saldo_anterior": saldo_actual,
                        "monto_usado": monto_usado, 
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
                "notas": f"Compra con adelanto. Total adelantos: {len(adelantos_actualizados)}",
                "registrado_por": update.effective_user.username or update.effective_user.first_name
            }
            
            # Guardar la compra
            append_data("compras", compra_data, COMPRAS_HEADERS)
            
            # Mostrar estrellas para la calidad
            estrellas = '⭐' * calidad
            
            # Detalles de los adelantos actualizados
            if adelantos_actualizados:
                adelantos_text = "\n📝 Adelantos utilizados:\n"
                for a in adelantos_actualizados:
                    adelantos_text += f"  • {a['fecha']}: {format_currency(a['saldo_anterior'])} → {format_currency(a['nuevo_saldo'])} "
                    adelantos_text += f"(Usado: {format_currency(a['monto_usado'])})\n"
            else:
                adelantos_text = "\n⚠️ No se actualizó ningún adelanto."
            
            # Confirmación al usuario
            await update.message.reply_text(
                "✅ COMPRA REGISTRADA CORRECTAMENTE\n\n"
                f"👨‍🌾 Proveedor: {proveedor}\n"
                f"📦 Cantidad: {cantidad} kg\n"
                f"💵 Precio por kg: {format_currency(precio)}\n"
                f"🏆 Calidad: {estrellas}\n"
                f"💰 Total: {format_currency(total)}\n\n"
                f"💳 Pagado con adelanto: {format_currency(monto_adelanto)}\n"
                f"💵 Pagado en efectivo: {format_currency(monto_efectivo)}\n"
                f"{adelantos_text}\n\n"
                f"Usa /compra_adelanto para registrar otra compra con adelanto o /compra para una compra normal."
            )
            
        else:
            await update.message.reply_text("❌ Compra cancelada. Puedes iniciar una nueva con /compra_adelanto.")
    except Exception as e:
        logger.error(f"Error al procesar compra con adelanto: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            "❌ Error al registrar la compra. Por favor, intenta nuevamente con /compra_adelanto."
        )
    
    # Limpiar datos de usuario
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar la conversación"""
    await update.message.reply_text(
        "❌ Operación cancelada. Puedes iniciar una nueva con /compra_adelanto."
    )
    context.user_data.clear()
    return ConversationHandler.END

# Handler para cuando el usuario envía un comando durante la conversación
async def comando_invalido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responder a comandos no esperados durante la conversación"""
    comando = update.message.text
    if comando == "/compra_adelanto":
        await update.message.reply_text(
            "⚠️ Ya estás en el proceso de compra con adelanto. "
            "Continúa con los pasos o usa /cancelar para reiniciar."
        )
    else:
        await update.message.reply_text(
            f"⚠️ Comando {comando} no válido durante el registro de compra con adelanto. "
            "Continúa con los pasos o usa /cancelar para cancelar el proceso."
        )

def register_compra_adelanto_handlers(application):
    """Registrar handlers para compra con adelanto"""
    # Crear manejador de conversación
    compra_adelanto_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compra_adelanto", compra_con_adelanto_command)],
        states={
            SELECCIONAR_PROVEEDOR: [
                CallbackQueryHandler(seleccionar_proveedor_callback)
            ],
            SELECCIONAR_ADELANTO: [
                CallbackQueryHandler(seleccionar_adelanto_callback)
            ],
            CANTIDAD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_step),
                CommandHandler("cancelar", cancelar),
                MessageHandler(filters.COMMAND, comando_invalido)
            ],
            PRECIO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, precio_step),
                CommandHandler("cancelar", cancelar),
                MessageHandler(filters.COMMAND, comando_invalido)
            ],
            CALIDAD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, calidad_step),
                CommandHandler("cancelar", cancelar),
                MessageHandler(filters.COMMAND, comando_invalido)
            ],
            CONFIRMAR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step),
                CommandHandler("cancelar", cancelar),
                MessageHandler(filters.COMMAND, comando_invalido)
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cancelar)
        ],
        # Usar per_chat=True para que solo se pueda ejecutar una conversación por chat
        per_chat=True,
        # Asegurarse de que los contextos de la conversación no se guarden por mucho tiempo
        conversation_timeout=900  # 15 minutos de timeout por inactividad
    )
    
    # Agregar el manejador a la aplicación
    application.add_handler(compra_adelanto_conv_handler)
    logger.info("Handlers de compra con adelanto registrados")