"""
Manejadores para la selección de adelantos
"""
import logging
import traceback
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.formatters import formatear_precio
from handlers.compra_mixta.config import (
    SELECCIONAR_ADELANTO, datos_compra_mixta, debug_log
)

logger = logging.getLogger(__name__)

async def seleccionar_adelanto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostrar adelantos disponibles para selección"""
    try:
        user_id = update.effective_user.id
        
        # Obtener la lista de adelantos disponibles
        adelantos = datos_compra_mixta[user_id].get("adelantos_disponibles", [])
        monto_adelanto = datos_compra_mixta[user_id].get("monto_adelanto", 0)
        
        if not adelantos:
            await update.message.reply_text(
                "❌ No hay adelantos disponibles para este proveedor."
            )
            return ConversationHandler.END
        
        # Crear teclado inline con los adelantos disponibles
        keyboard = []
        for adelanto in adelantos:
            fecha = adelanto.get('fecha', '')
            
            # Extraer y validar el saldo
            saldo_str = adelanto.get('saldo_restante', '0')
            try:
                saldo = 0
                if saldo_str:
                    saldo = float(str(saldo_str).replace(',', '.'))
            except (ValueError, TypeError):
                debug_log(f"Error al convertir saldo_restante: '{saldo_str}'")
                saldo = 0
            
            adelanto_id = adelanto.get('_row_index', '')
            
            keyboard.append([
                InlineKeyboardButton(
                    f"Adelanto {fecha} - {formatear_precio(saldo)}",
                    callback_data=f"adelanto_{adelanto_id}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Si ya tenemos un monto de adelanto calculado (para métodos combinados)
        if monto_adelanto > 0:
            await update.message.reply_text(
                f"💰 Monto a pagar con adelanto: {formatear_precio(monto_adelanto)}\n\n"
                "Selecciona el adelanto que deseas utilizar:",
                reply_markup=reply_markup
            )
        else:
            # Para método de pago solo adelanto
            datos_compra_mixta[user_id]["monto_adelanto"] = datos_compra_mixta[user_id]["preciototal"]
            
            await update.message.reply_text(
                f"💰 Total a pagar con adelanto: {formatear_precio(datos_compra_mixta[user_id]['preciototal'])}\n\n"
                "Selecciona el adelanto que deseas utilizar:",
                reply_markup=reply_markup
            )
        
        return SELECCIONAR_ADELANTO
    except Exception as e:
        logger.error(f"Error en seleccionar_adelanto: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        if update.message:
            await update.message.reply_text(
                "❌ Ha ocurrido un error al seleccionar adelantos. Por favor, intenta nuevamente."
            )
        else:
            chat_id = update.callback_query.message.chat_id
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Ha ocurrido un error al seleccionar adelantos. Por favor, intenta nuevamente."
            )
        return ConversationHandler.END

async def seleccionar_adelanto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar la selección de adelanto"""
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        # Extraer el ID del adelanto seleccionado
        adelanto_id = query.data.replace("adelanto_", "")
        
        # Guardar el ID del adelanto
        datos_compra_mixta[user_id]["adelanto_id"] = adelanto_id
        
        # Encontrar el adelanto seleccionado
        adelantos = datos_compra_mixta[user_id].get("adelantos_disponibles", [])
        adelanto_seleccionado = None
        
        for adelanto in adelantos:
            if str(adelanto.get('_row_index', '')) == str(adelanto_id):
                adelanto_seleccionado = adelanto
                break
        
        if adelanto_seleccionado:
            fecha = adelanto_seleccionado.get('fecha', '')
            
            # Extraer y validar el saldo
            saldo_str = adelanto_seleccionado.get('saldo_restante', '0')
            try:
                saldo = 0
                if saldo_str:
                    saldo = float(str(saldo_str).replace(',', '.'))
            except (ValueError, TypeError):
                debug_log(f"Error al convertir saldo_restante: '{saldo_str}'")
                saldo = 0
            
            # Verificar si hay suficiente saldo
            monto_adelanto = datos_compra_mixta[user_id].get("monto_adelanto", 0)
            
            if monto_adelanto > saldo:
                # Editar el mensaje para mostrar error
                await query.edit_message_text(
                    f"❌ El adelanto seleccionado no tiene suficiente saldo.\n\n"
                    f"Saldo disponible: {formatear_precio(saldo)}\n"
                    f"Monto requerido: {formatear_precio(monto_adelanto)}\n\n"
                    "Por favor, selecciona otro adelanto o cambia el método de pago."
                )
                return ConversationHandler.END
            
            # Editar el mensaje para mostrar confirmación
            await query.edit_message_text(
                f"✅ Adelanto seleccionado: {fecha}\n"
                f"Saldo disponible: {formatear_precio(saldo)}\n"
                f"Monto a utilizar: {formatear_precio(monto_adelanto)}"
            )
            
            # Guardar información detallada del adelanto
            datos_compra_mixta[user_id]["adelanto_fecha"] = fecha
            datos_compra_mixta[user_id]["adelanto_saldo"] = saldo
            
            # Importar aquí para evitar importación circular
            from handlers.compra_mixta.steps_resumen import mostrar_resumen
            
            # Mostrar resumen final
            return await mostrar_resumen(update, context)
        else:
            await query.edit_message_text("❌ Error al seleccionar el adelanto. Por favor, intenta nuevamente.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error en seleccionar_adelanto_callback: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        try:
            await update.callback_query.edit_message_text(
                "❌ Ha ocurrido un error al procesar tu selección. Por favor, intenta nuevamente."
            )
        except:
            # Si no se puede editar el mensaje original
            chat_id = update.callback_query.message.chat_id
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Ha ocurrido un error al procesar tu selección. Por favor, intenta nuevamente."
            )
        return ConversationHandler.END
