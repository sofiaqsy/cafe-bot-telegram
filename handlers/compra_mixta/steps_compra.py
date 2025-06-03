"""
Manejadores para las etapas de datos de compra: cantidad, precio y método de pago
"""
import logging
import traceback
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.helpers import calculate_total
from utils.formatters import formatear_numero, formatear_precio, procesar_entrada_numerica
from handlers.compra_mixta.config import (
    CANTIDAD, PRECIO, METODO_PAGO, 
    MONTO_EFECTIVO, MONTO_TRANSFERENCIA, MONTO_ADELANTO,
    METODOS_PAGO, datos_compra_mixta, debug_log
)
from handlers.compra_mixta.steps_adelanto import seleccionar_adelanto
from handlers.compra_mixta.steps_resumen import mostrar_resumen

logger = logging.getLogger(__name__)

async def cantidad_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la cantidad y solicitar el precio"""
    try:
        user_id = update.effective_user.id
        cantidad_text = update.message.text.strip()
        
        try:
            cantidad = procesar_entrada_numerica(cantidad_text)
            
            if cantidad <= 0:
                await update.message.reply_text("❌ La cantidad debe ser mayor a cero. Intenta nuevamente:")
                return CANTIDAD
            
            datos_compra_mixta[user_id]["cantidad"] = cantidad
            
            await update.message.reply_text(
                f"📦 Cantidad: {formatear_numero(cantidad)} kg\n\n"
                "Ahora, ingresa el precio por kg:"
            )
            return PRECIO
        except ValueError as e:
            logger.warning(f"Valor inválido para cantidad: {cantidad_text} - {e}")
            await update.message.reply_text(
                "❌ Por favor, ingresa un número válido para la cantidad."
            )
            return CANTIDAD
    except Exception as e:
        logger.error(f"Error en cantidad_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar la cantidad. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def precio_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el precio y solicitar método de pago"""
    try:
        user_id = update.effective_user.id
        precio_text = update.message.text.strip()
        
        try:
            precio = procesar_entrada_numerica(precio_text)
            
            if precio <= 0:
                await update.message.reply_text("❌ El precio debe ser mayor a cero. Intenta nuevamente:")
                return PRECIO
            
            datos_compra_mixta[user_id]["precio"] = precio
            
            # Calcular total
            cantidad = datos_compra_mixta[user_id]["cantidad"]
            total = calculate_total(cantidad, precio)
            datos_compra_mixta[user_id]["preciototal"] = total
            
            # Crear teclado con métodos de pago disponibles
            keyboard = []
            
            # Solo mostrar opciones con adelanto si el proveedor tiene adelantos disponibles
            if datos_compra_mixta[user_id].get("tiene_adelantos", False):
                debug_log(f"Mostrando todos los métodos de pago incluyendo adelantos para usuario {user_id}")
                metodos = METODOS_PAGO
            else:
                # Filtrar métodos que incluyen adelanto
                debug_log(f"Filtrando métodos de pago sin adelantos para usuario {user_id}")
                metodos = [m for m in METODOS_PAGO if "ADELANTO" not in m]
            
            for metodo in metodos:
                keyboard.append([metodo])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                f"💵 Precio por kg: {formatear_precio(precio)}\n"
                f"💰 Total a pagar: {formatear_precio(total)}\n\n"
                "Selecciona el método de pago:",
                reply_markup=reply_markup
            )
            return METODO_PAGO
        except ValueError as e:
            logger.warning(f"Valor inválido para precio: {precio_text} - {e}")
            await update.message.reply_text(
                "❌ Por favor, ingresa un número válido para el precio."
            )
            return PRECIO
    except Exception as e:
        logger.error(f"Error en precio_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar el precio. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def metodo_pago_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar el método de pago seleccionado y dirigir al flujo correspondiente"""
    try:
        user_id = update.effective_user.id
        metodo_pago = update.message.text.strip().upper()
        
        # Validar que sea un método de pago válido
        metodos_validos = METODOS_PAGO
        if not datos_compra_mixta[user_id].get("tiene_adelantos", False):
            metodos_validos = [m for m in METODOS_PAGO if "ADELANTO" not in m]
        
        if metodo_pago not in metodos_validos:
            # Mostrar opciones válidas
            keyboard = []
            for metodo in metodos_validos:
                keyboard.append([metodo])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                "❌ Método de pago no válido. Por favor, selecciona una de las opciones disponibles:",
                reply_markup=reply_markup
            )
            return METODO_PAGO
        
        # Guardar el método de pago
        datos_compra_mixta[user_id]["metodo_pago"] = metodo_pago
        debug_log(f"Usuario {user_id} seleccionó método de pago: {metodo_pago}")
        
        # Determinar el siguiente paso según el método de pago
        if metodo_pago == "EFECTIVO":
            # Si es solo efectivo, el monto es el total
            datos_compra_mixta[user_id]["monto_efectivo"] = datos_compra_mixta[user_id]["preciototal"]
            return await mostrar_resumen(update, context)
        
        elif metodo_pago == "TRANSFERENCIA":
            # Si es solo transferencia, el monto es el total
            datos_compra_mixta[user_id]["monto_transferencia"] = datos_compra_mixta[user_id]["preciototal"]
            return await mostrar_resumen(update, context)
        
        elif metodo_pago == "EFECTIVO Y TRANSFERENCIA":
            # Solicitar el monto en efectivo
            await update.message.reply_text(
                f"💰 Total a pagar: {formatear_precio(datos_compra_mixta[user_id]['preciototal'])}\n\n"
                "¿Cuánto se pagará en efectivo?",
                reply_markup=ReplyKeyboardRemove()
            )
            return MONTO_EFECTIVO
        
        elif metodo_pago == "ADELANTO":
            # Si es solo adelanto, redirigir a la selección de adelanto
            return await seleccionar_adelanto(update, context)
        
        elif metodo_pago == "EFECTIVO Y ADELANTO":
            # Solicitar el monto en efectivo
            await update.message.reply_text(
                f"💰 Total a pagar: {formatear_precio(datos_compra_mixta[user_id]['preciototal'])}\n\n"
                "¿Cuánto se pagará en efectivo?",
                reply_markup=ReplyKeyboardRemove()
            )
            return MONTO_EFECTIVO
        
        elif metodo_pago == "TRANSFERENCIA Y ADELANTO":
            # Solicitar el monto por transferencia
            await update.message.reply_text(
                f"💰 Total a pagar: {formatear_precio(datos_compra_mixta[user_id]['preciototal'])}\n\n"
                "¿Cuánto se pagará por transferencia?",
                reply_markup=ReplyKeyboardRemove()
            )
            return MONTO_TRANSFERENCIA
            
        # NUEVAS OPCIONES
        elif metodo_pago == "ADELANTO Y EFECTIVO":
            # Solicitar cuánto adelanto se utilizará
            await update.message.reply_text(
                f"💰 Total a pagar: {formatear_precio(datos_compra_mixta[user_id]['preciototal'])}\n\n"
                "¿Cuánto se pagará con adelanto?",
                reply_markup=ReplyKeyboardRemove()
            )
            return MONTO_ADELANTO
            
        elif metodo_pago == "ADELANTO Y TRANSFERENCIA":
            # Solicitar cuánto adelanto se utilizará
            await update.message.reply_text(
                f"💰 Total a pagar: {formatear_precio(datos_compra_mixta[user_id]['preciototal'])}\n\n"
                "¿Cuánto se pagará con adelanto?",
                reply_markup=ReplyKeyboardRemove()
            )
            return MONTO_ADELANTO
            
        elif metodo_pago == "ADELANTO Y POR PAGAR":
            # Solicitar cuánto adelanto se utilizará
            await update.message.reply_text(
                f"💰 Total a pagar: {formatear_precio(datos_compra_mixta[user_id]['preciototal'])}\n\n"
                "¿Cuánto se pagará con adelanto?",
                reply_markup=ReplyKeyboardRemove()
            )
            return MONTO_ADELANTO
            
    except Exception as e:
        logger.error(f"Error en metodo_pago_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar el método de pago. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END
