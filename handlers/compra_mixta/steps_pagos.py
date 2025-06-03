"""
Manejadores para las etapas de pago: montos de efectivo, transferencia y adelanto
"""
import logging
import traceback
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.formatters import formatear_precio, procesar_entrada_numerica
from handlers.compra_mixta.config import (
    MONTO_EFECTIVO, MONTO_TRANSFERENCIA, MONTO_ADELANTO,
    datos_compra_mixta, debug_log
)
from handlers.compra_mixta.steps_adelanto import seleccionar_adelanto
from handlers.compra_mixta.steps_resumen import mostrar_resumen

logger = logging.getLogger(__name__)

async def monto_efectivo_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar el monto en efectivo"""
    try:
        user_id = update.effective_user.id
        monto_text = update.message.text.strip()
        
        try:
            monto_efectivo = procesar_entrada_numerica(monto_text)
            
            total = datos_compra_mixta[user_id]["preciototal"]
            
            if monto_efectivo < 0:
                await update.message.reply_text("❌ El monto en efectivo no puede ser negativo. Intenta nuevamente:")
                return MONTO_EFECTIVO
            
            if monto_efectivo > total:
                await update.message.reply_text(
                    f"❌ El monto en efectivo no puede superar el total a pagar ({formatear_precio(total)}). "
                    "Intenta nuevamente:"
                )
                return MONTO_EFECTIVO
            
            # Guardar el monto en efectivo
            datos_compra_mixta[user_id]["monto_efectivo"] = monto_efectivo
            
            # Determinar el siguiente paso según el método de pago
            metodo_pago = datos_compra_mixta[user_id]["metodo_pago"]
            
            if metodo_pago == "EFECTIVO Y TRANSFERENCIA":
                # Calcular el monto por transferencia automáticamente
                monto_transferencia = total - monto_efectivo
                datos_compra_mixta[user_id]["monto_transferencia"] = monto_transferencia
                
                await update.message.reply_text(
                    f"💵 Monto en efectivo: {formatear_precio(monto_efectivo)}\n"
                    f"🏦 Monto por transferencia: {formatear_precio(monto_transferencia)}"
                )
                
                return await mostrar_resumen(update, context)
            
            elif metodo_pago == "EFECTIVO Y ADELANTO":
                # Calcular el monto de adelanto automáticamente
                monto_adelanto = total - monto_efectivo
                
                # Verificar que hay suficiente saldo en adelantos
                saldo_disponible = datos_compra_mixta[user_id].get("saldo_adelantos", 0)
                
                if monto_adelanto > saldo_disponible:
                    await update.message.reply_text(
                        f"❌ El monto de adelanto requerido ({formatear_precio(monto_adelanto)}) "
                        f"supera el saldo disponible ({formatear_precio(saldo_disponible)}).\n\n"
                        "Por favor, ingresa un monto en efectivo mayor:"
                    )
                    return MONTO_EFECTIVO
                
                # Guardar el monto de adelanto y pasar a selección de adelanto
                datos_compra_mixta[user_id]["monto_adelanto"] = monto_adelanto
                
                return await seleccionar_adelanto(update, context)
        except ValueError as e:
            logger.warning(f"Valor inválido para monto_efectivo: {monto_text} - {e}")
            await update.message.reply_text(
                "❌ Por favor, ingresa un número válido para el monto en efectivo."
            )
            return MONTO_EFECTIVO
    except Exception as e:
        logger.error(f"Error en monto_efectivo_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar el monto en efectivo. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def monto_transferencia_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar el monto por transferencia"""
    try:
        user_id = update.effective_user.id
        monto_text = update.message.text.strip()
        
        try:
            monto_transferencia = procesar_entrada_numerica(monto_text)
            
            total = datos_compra_mixta[user_id]["preciototal"]
            
            if monto_transferencia < 0:
                await update.message.reply_text("❌ El monto por transferencia no puede ser negativo. Intenta nuevamente:")
                return MONTO_TRANSFERENCIA
            
            if monto_transferencia > total:
                await update.message.reply_text(
                    f"❌ El monto por transferencia no puede superar el total a pagar ({formatear_precio(total)}). "
                    "Intenta nuevamente:"
                )
                return MONTO_TRANSFERENCIA
            
            # Guardar el monto por transferencia
            datos_compra_mixta[user_id]["monto_transferencia"] = monto_transferencia
            
            # Determinar el siguiente paso según el método de pago
            metodo_pago = datos_compra_mixta[user_id]["metodo_pago"]
            
            if metodo_pago == "TRANSFERENCIA Y ADELANTO":
                # Calcular el monto de adelanto automáticamente
                monto_adelanto = total - monto_transferencia
                
                # Verificar que hay suficiente saldo en adelantos
                saldo_disponible = datos_compra_mixta[user_id].get("saldo_adelantos", 0)
                
                if monto_adelanto > saldo_disponible:
                    await update.message.reply_text(
                        f"❌ El monto de adelanto requerido ({formatear_precio(monto_adelanto)}) "
                        f"supera el saldo disponible ({formatear_precio(saldo_disponible)}).\n\n"
                        "Por favor, ingresa un monto por transferencia mayor:"
                    )
                    return MONTO_TRANSFERENCIA
                
                # Guardar el monto de adelanto y pasar a selección de adelanto
                datos_compra_mixta[user_id]["monto_adelanto"] = monto_adelanto
                
                return await seleccionar_adelanto(update, context)
        except ValueError as e:
            logger.warning(f"Valor inválido para monto_transferencia: {monto_text} - {e}")
            await update.message.reply_text(
                "❌ Por favor, ingresa un número válido para el monto por transferencia."
            )
            return MONTO_TRANSFERENCIA
    except Exception as e:
        logger.error(f"Error en monto_transferencia_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar el monto por transferencia. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def monto_adelanto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar el monto de adelanto cuando el formato es 'ADELANTO Y X'"""
    try:
        user_id = update.effective_user.id
        monto_text = update.message.text.strip()
        
        try:
            monto_adelanto = procesar_entrada_numerica(monto_text)
            
            total = datos_compra_mixta[user_id]["preciototal"]
            
            if monto_adelanto < 0:
                await update.message.reply_text("❌ El monto de adelanto no puede ser negativo. Intenta nuevamente:")
                return MONTO_ADELANTO
            
            if monto_adelanto > total:
                await update.message.reply_text(
                    f"❌ El monto de adelanto no puede superar el total a pagar ({formatear_precio(total)}). "
                    "Intenta nuevamente:"
                )
                return MONTO_ADELANTO
                
            # Verificar que hay suficiente saldo en adelantos
            saldo_disponible = datos_compra_mixta[user_id].get("saldo_adelantos", 0)
            
            if monto_adelanto > saldo_disponible:
                await update.message.reply_text(
                    f"❌ El monto de adelanto ({formatear_precio(monto_adelanto)}) "
                    f"supera el saldo disponible ({formatear_precio(saldo_disponible)}).\n\n"
                    "Por favor, ingresa un monto menor:"
                )
                return MONTO_ADELANTO
            
            # Guardar el monto de adelanto
            datos_compra_mixta[user_id]["monto_adelanto"] = monto_adelanto
            
            # Determinar el siguiente paso según el método de pago
            metodo_pago = datos_compra_mixta[user_id]["metodo_pago"]
            
            if metodo_pago == "ADELANTO Y EFECTIVO":
                # Calcular automáticamente el monto en efectivo
                monto_efectivo = total - monto_adelanto
                datos_compra_mixta[user_id]["monto_efectivo"] = monto_efectivo
                
                await update.message.reply_text(
                    f"💳 Monto con adelanto: {formatear_precio(monto_adelanto)}\n"
                    f"💵 Monto en efectivo: {formatear_precio(monto_efectivo)}"
                )
                
                # Pasar a selección de adelanto
                return await seleccionar_adelanto(update, context)
                
            elif metodo_pago == "ADELANTO Y TRANSFERENCIA":
                # Calcular automáticamente el monto por transferencia
                monto_transferencia = total - monto_adelanto
                datos_compra_mixta[user_id]["monto_transferencia"] = monto_transferencia
                
                await update.message.reply_text(
                    f"💳 Monto con adelanto: {formatear_precio(monto_adelanto)}\n"
                    f"🏦 Monto por transferencia: {formatear_precio(monto_transferencia)}"
                )
                
                # Pasar a selección de adelanto
                return await seleccionar_adelanto(update, context)
                
            elif metodo_pago == "ADELANTO Y POR PAGAR":
                # Calcular automáticamente el monto por pagar
                monto_por_pagar = total - monto_adelanto
                datos_compra_mixta[user_id]["monto_por_pagar"] = monto_por_pagar
                
                await update.message.reply_text(
                    f"💳 Monto con adelanto: {formatear_precio(monto_adelanto)}\n"
                    f"🔄 Monto por pagar: {formatear_precio(monto_por_pagar)}"
                )
                
                # Pasar a selección de adelanto
                return await seleccionar_adelanto(update, context)
                
        except ValueError as e:
            logger.warning(f"Valor inválido para monto_adelanto: {monto_text} - {e}")
            await update.message.reply_text(
                "❌ Por favor, ingresa un número válido para el monto de adelanto."
            )
            return MONTO_ADELANTO
    except Exception as e:
        logger.error(f"Error en monto_adelanto_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar el monto de adelanto. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END
