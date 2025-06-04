"""
Archivo principal con la corrección para el método de compra_mixta.
La corrección incluye:
1. Eliminar la llamada a update_almacen para evitar duplicidad en almacén
2. Corregir el tipo de dato del adelanto_id al actualizar el saldo
"""
import logging
import traceback
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler
)

from utils.sheets import append_data as append_sheets, generate_unique_id, get_all_data, get_filtered_data, update_cell
from utils.helpers import get_now_peru, safe_float, format_date_for_sheets, format_currency, calculate_total
from utils.formatters import formatear_numero, formatear_precio, procesar_entrada_numerica

# Configurar logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Estados para la conversación
TIPO_CAFE, PROVEEDOR, CANTIDAD, PRECIO, METODO_PAGO, MONTO_EFECTIVO, MONTO_TRANSFERENCIA, SELECCIONAR_ADELANTO, CONFIRMAR = range(9)

# Tipos de café predefinidos
TIPOS_CAFE = ["CEREZO", "MOTE", "PERGAMINO"]

# Métodos de pago disponibles
METODOS_PAGO = [
    "EFECTIVO", 
    "TRANSFERENCIA", 
    "EFECTIVO Y TRANSFERENCIA", 
    "ADELANTO", 
    "EFECTIVO Y ADELANTO", 
    "TRANSFERENCIA Y ADELANTO"
]

# Datos temporales
datos_compra_mixta = {}

def debug_log(message):
    """Función especial para logs de depuración más visibles"""
    logger.debug(f"### DEBUG ### {message}")
    logger.info(f"### DEBUG ### {message}")

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
                        
                        # CORRECCIÓN: Asegurar que adelanto_id sea un entero
                        adelanto_id_int = int(datos["adelanto_id"])
                        
                        # Actualizar el saldo en la hoja de adelantos
                        result_adelanto = update_cell("adelantos", adelanto_id_int, "saldo_restante", nuevo_saldo_formateado)
                        logger.info(f"Actualizado saldo de adelanto {datos['adelanto_id']} a {nuevo_saldo_formateado}")
                        
                        if result_adelanto:
                            mensaje_adelanto = f"✅ Saldo de adelanto actualizado correctamente a {formatear_precio(nuevo_saldo_formateado)}\\n\\n"
                        else:
                            mensaje_adelanto = "⚠️ No se pudo actualizar el saldo de adelanto\\n\\n"
                    except Exception as e:
                        logger.error(f"Error al actualizar saldo de adelanto: {e}")
                        logger.error(traceback.format_exc())
                        mensaje_adelanto = "⚠️ Error al actualizar saldo de adelanto\\n\\n"
                
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
                
                # 2. Guardar también en la hoja de compras_mixtas para detalles adicionales
                logger.info(f"Guardando compra mixta en hoja de compras_mixtas: {datos}")
                result_mixta = append_sheets("compras_mixtas", datos)
                
                # 3. No es necesario registrar en almacén manualmente - append_sheets("compras", ...) ya lo hace automáticamente
                # CORRECCIÓN: Eliminada la llamada a update_almacen para evitar duplicaciones
                logger.info(f"La compra se registró automáticamente en almacén por el proceso de append_sheets")
                result_almacen = True  # Asumimos que el proceso automático funcionó
                
                if result_compra:
                    logger.info(f"Compra mixta guardada exitosamente para usuario {user_id}")
                    
                    # Mensaje de éxito - sin usar Markdown para evitar errores de parseo
                    mensaje_exito = "✅ ¡COMPRA MIXTA REGISTRADA EXITOSAMENTE!\\n\\n"
                    mensaje_exito += f"ID: {datos['id']}\\n"
                    mensaje_exito += f"Proveedor: {datos['proveedor']}\\n"
                    mensaje_exito += f"Total: {formatear_precio(datos['preciototal'])}\\n\\n"
                    
                    # Añadir información sobre saldo de adelanto si aplica
                    if datos.get("monto_adelanto", 0) > 0:
                        mensaje_exito += mensaje_adelanto
                    
                    # Añadir información sobre almacén
                    mensaje_exito += "✅ Registrado en almacén correctamente\\n\\n"
                    
                    # Información sobre la hoja de compras_mixtas
                    if result_mixta:
                        mensaje_exito += "✅ Detalles del pago mixto guardados correctamente\\n\\n"
                    else:
                        mensaje_exito += "⚠️ La compra se registró pero hubo un error al guardar los detalles del pago mixto\\n\\n"
                    
                    mensaje_exito += "Usa /compra_mixta para registrar otra compra."
                    
                    await update.message.reply_text(
                        mensaje_exito,
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    logger.error(f"Error al guardar compra mixta: La función append_sheets devolvió False")
                    await update.message.reply_text(
                        "❌ Error al guardar la compra. Por favor, intenta nuevamente.\\n\\n"\
                        "Contacta al administrador si el problema persiste.",
                        reply_markup=ReplyKeyboardRemove()
                    )
            except Exception as e:
                logger.error(f"Error al procesar compra mixta: {e}")
                logger.error(traceback.format_exc())
                
                await update.message.reply_text(
                    "❌ Error al registrar la compra. Por favor, intenta nuevamente.\\n\\n"\
                    f"Error: {str(e)}\\n\\n"\
                    "Contacta al administrador si el problema persiste.",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            logger.info(f"Usuario {user_id} canceló la compra mixta")
            
            await update.message.reply_text(
                "❌ Compra cancelada.\\n\\n"\
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
