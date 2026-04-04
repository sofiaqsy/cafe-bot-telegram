"""
Manejadores para mostrar resumen y confirmación de la compra
"""
import logging
import traceback
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.helpers import get_now_peru, format_date_for_sheets
from utils.formatters import formatear_numero, formatear_precio
from utils.sheets import append_data as append_sheets, generate_unique_id, update_cell
from utils.sheets.almacen import update_almacen
from handlers.compra_mixta.config import (
    CONFIRMAR, datos_compra_mixta, debug_log
)

logger = logging.getLogger(__name__)

async def mostrar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostrar resumen de la compra y solicitar confirmación"""
    try:
        user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
        
        # Obtener los datos de la compra
        datos = datos_compra_mixta[user_id]
        
        # Crear resumen con los datos pero sin usar caracteres especiales o formateo Markdown
        resumen = "📋 RESUMEN DE COMPRA MIXTA\n\n"
        resumen += f"☕ Tipo de café: {datos.get('tipo_cafe', '')}\n"
        resumen += f"👨‍🌾 Proveedor: {datos.get('proveedor', '')}\n"
        resumen += f"📦 Cantidad: {formatear_numero(datos.get('cantidad', 0))} kg\n"
        resumen += f"💵 Precio por kg: {formatear_precio(datos.get('precio', 0))}\n"
        resumen += f"💰 Total a pagar: {formatear_precio(datos.get('preciototal', 0))}\n\n"
        
        resumen += f"💳 Método de pago: {datos.get('metodo_pago', '')}\n"
        
        # Añadir detalles según el método de pago
        if datos.get("monto_efectivo", 0) > 0:
            resumen += f"💵 Monto en efectivo: {formatear_precio(datos.get('monto_efectivo', 0))}\n"
        
        if datos.get("monto_transferencia", 0) > 0:
            resumen += f"🏦 Monto por transferencia: {formatear_precio(datos.get('monto_transferencia', 0))}\n"
        
        if datos.get("monto_adelanto", 0) > 0:
            resumen += f"💳 Monto con adelanto: {formatear_precio(datos.get('monto_adelanto', 0))}\n"
            
            # Si hay información de adelanto, mostrarla
            if datos.get("adelanto_fecha", ""):
                resumen += f"📅 Adelanto de fecha: {datos.get('adelanto_fecha', '')}\n"
                
                # Calcular el nuevo saldo del adelanto
                nuevo_saldo = datos.get("adelanto_saldo", 0) - datos.get("monto_adelanto", 0)
                resumen += f"💰 Nuevo saldo de adelanto: {formatear_precio(nuevo_saldo)}\n"
        
        # Añadir información sobre el monto por pagar si existe
        if datos.get("monto_por_pagar", 0) > 0:
            resumen += f"🔄 Monto por pagar: {formatear_precio(datos.get('monto_por_pagar', 0))}\n"
        
        # Crear teclado para confirmación
        keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Enviar mensaje según el tipo de actualización
        if update.message:
            await update.message.reply_text(
                resumen + "\n¿Confirmas esta compra?",
                reply_markup=reply_markup
            )
        else:
            # Si venimos de un callback, enviar un nuevo mensaje
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=resumen + "\n¿Confirmas esta compra?",
                reply_markup=reply_markup
            )
        
        return CONFIRMAR
    except Exception as e:
        logger.error(f"Error en mostrar_resumen: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ Ha ocurrido un error al mostrar el resumen. Por favor, intenta nuevamente.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y registrar la compra mixta"""
    try:
        user_id = update.effective_user.id
        respuesta = update.message.text.lower()
        
        if respuesta in ['sí', 'si', 's', 'yes', 'y', '✅ confirmar', 'confirmar']:
            try:
                # Obtener los datos de la compra
                datos = datos_compra_mixta[user_id].copy()
                
                # Generar un ID único para esta compra
                compra_id = generate_unique_id("CM-", 6)
                datos["id"] = compra_id
                
                # Añadir fecha actualizada con formato protegido para Google Sheets
                now = get_now_peru()
                fecha_formateada = now.strftime("%Y-%m-%d %H:%M")
                datos["fecha"] = format_date_for_sheets(fecha_formateada)
                
                # Añadir notas vacías (para mantener estructura)
                datos["notas"] = ""
                
                # Si se utiliza adelanto, actualizar el saldo del adelanto
                result_adelanto = False
                mensaje_adelanto = ""
                
                if datos.get("monto_adelanto", 0) > 0 and datos.get("adelanto_id", ""):
                    try:
                        # Calcular el nuevo saldo
                        nuevo_saldo = datos.get("adelanto_saldo", 0) - datos.get("monto_adelanto", 0)
                        
                        # Log para debug
                        debug_log(f"Actualizando adelanto ID: {datos['adelanto_id']} - Nuevo saldo: {nuevo_saldo}")
                        
                        # Formatear el nuevo saldo a dos decimales
                        nuevo_saldo_formateado = round(nuevo_saldo, 2)
                        
                        # Actualizar el saldo en la hoja de adelantos
                        result_adelanto = update_cell("adelantos", datos["adelanto_id"], "saldo_restante", nuevo_saldo_formateado)
                        logger.info(f"Actualizado saldo de adelanto {datos['adelanto_id']} a {nuevo_saldo_formateado}")
                        
                        if result_adelanto:
                            mensaje_adelanto = f"✅ Saldo de adelanto actualizado correctamente a {formatear_precio(nuevo_saldo_formateado)}\n\n"
                        else:
                            mensaje_adelanto = "⚠️ No se pudo actualizar el saldo de adelanto\n\n"
                    except Exception as e:
                        logger.error(f"Error al actualizar saldo de adelanto: {e}")
                        logger.error(traceback.format_exc())
                        mensaje_adelanto = "⚠️ Error al actualizar saldo de adelanto\n\n"
                
                # 1. Guardar en la hoja de compras regular primero
                logger.info(f"Guardando la compra mixta en la hoja de compras regular")
                datos_compra_regular = {
                    "id": compra_id,
                    "fecha": datos["fecha"],
                    "tipo_cafe": datos["tipo_cafe"],
                    "proveedor": datos["proveedor"],
                    "cantidad": datos["cantidad"],
                    "precio": datos["precio"],
                    "preciototal": datos["preciototal"],
                    "registrado_por": datos["registrado_por"],
                    "notas": f"Compra mixta - Método de pago: {datos['metodo_pago']}"
                }
                result_compra = append_sheets("compras", datos_compra_regular)

                # Sync stock to apartalo-core (PERGAMINO or CEREZO)
                if result_compra:
                    try:
                        from utils.apartalo import agregar_stock
                        agregar_stock(
                            datos.get("tipo_cafe", ""),
                            float(datos.get("cantidad", 0)),
                            motivo=f"Compra mixta {compra_id} - {datos.get('proveedor','')}"
                        )
                    except Exception as e:
                        logger.error(f"[APARTALO] Error sincronizando stock (mixta): {e}")

                # 2. Guardar también en la hoja de compras_mixtas para detalles adicionales
                logger.info(f"Guardando compra mixta en hoja de compras_mixtas: {datos}")
                result_mixta = append_sheets("compras_mixtas", datos)
                
                # 3. Registrar en almacén con manejo adecuado del tipo de retorno
                logger.info(f"Registrando la compra en almacén")
                result_almacen = False
                try:
                    # Llamar a update_almacen con manejo explícito del tipo de retorno
                    result = update_almacen(
                        fase=datos["tipo_cafe"],
                        cantidad_cambio=datos["cantidad"],
                        operacion="sumar",
                        notas=f"Compra mixta ID: {compra_id}",
                        compra_id=compra_id
                    )
                    
                    # La función update_almacen puede devolver un booleano o una tupla (bool, str)
                    # dependiendo del tipo de operación
                    if isinstance(result, tuple):
                        result_almacen = result[0]  # Extraer el booleano de la tupla
                    else:
                        result_almacen = result  # Ya es un booleano
                    
                    logger.info(f"Resultado de update_almacen: {result_almacen}")
                except Exception as e:
                    logger.error(f"Error al actualizar almacén: {e}")
                    logger.error(traceback.format_exc())
                    result_almacen = False
                
                if result_compra:
                    logger.info(f"Compra mixta guardada exitosamente para usuario {user_id}")
                    
                    # Mensaje de éxito - sin usar Markdown para evitar errores de parseo
                    mensaje_exito = "✅ ¡COMPRA MIXTA REGISTRADA EXITOSAMENTE!\n\n"
                    mensaje_exito += f"ID: {datos['id']}\n"
                    mensaje_exito += f"Proveedor: {datos['proveedor']}\n"
                    mensaje_exito += f"Total: {formatear_precio(datos['preciototal'])}\n\n"
                    
                    # Añadir información sobre saldo de adelanto si aplica
                    if datos.get("monto_adelanto", 0) > 0:
                        mensaje_exito += mensaje_adelanto
                    
                    # Añadir información sobre almacén
                    if result_almacen:
                        mensaje_exito += "✅ Registrado en almacén correctamente\n\n"
                    else:
                        mensaje_exito += "⚠️ La compra se registró pero hubo un error al actualizar el almacén\n\n"
                    
                    # Información sobre la hoja de compras_mixtas
                    if result_mixta:
                        mensaje_exito += "✅ Detalles del pago mixto guardados correctamente\n\n"
                    else:
                        mensaje_exito += "⚠️ La compra se registró pero hubo un error al guardar los detalles del pago mixto\n\n"
                    
                    mensaje_exito += "Usa /compra_mixta para registrar otra compra."
                    
                    await update.message.reply_text(
                        mensaje_exito,
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    logger.error(f"Error al guardar compra mixta: La función append_sheets devolvió False")
                    await update.message.reply_text(
                        "❌ Error al guardar la compra. Por favor, intenta nuevamente.\n\n"
                        "Contacta al administrador si el problema persiste.",
                        reply_markup=ReplyKeyboardRemove()
                    )
            except Exception as e:
                logger.error(f"Error al procesar compra mixta: {e}")
                logger.error(traceback.format_exc())
                
                await update.message.reply_text(
                    "❌ Error al registrar la compra. Por favor, intenta nuevamente.\n\n"
                    f"Error: {str(e)}\n\n"
                    "Contacta al administrador si el problema persiste.",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            logger.info(f"Usuario {user_id} canceló la compra mixta")
            
            await update.message.reply_text(
                "❌ Compra cancelada.\n\n"
                "Usa /compra_mixta para iniciar de nuevo.",
                reply_markup=ReplyKeyboardRemove()
            )
        
        # Limpiar datos temporales
        if user_id in datos_compra_mixta:
            del datos_compra_mixta[user_id]
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error en confirmar_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al confirmar la compra. Por favor, intenta nuevamente.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales para evitar problemas futuros
        if user_id in datos_compra_mixta:
            del datos_compra_mixta[user_id]
            
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar la conversación"""
    try:
        user_id = update.effective_user.id
        logger.info(f"Usuario {user_id} canceló el proceso de compra mixta con /cancelar")
        
        # Limpiar datos temporales
        if user_id in datos_compra_mixta:
            del datos_compra_mixta[user_id]
        
        await update.message.reply_text(
            "❌ Operación cancelada.\n\n"
            "Usa /compra_mixta para iniciar de nuevo cuando quieras.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error en cancelar: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error, pero la operación ha sido cancelada.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales para evitar problemas futuros
        if 'user_id' in locals() and user_id in datos_compra_mixta:
            del datos_compra_mixta[user_id]
            
        return ConversationHandler.END
