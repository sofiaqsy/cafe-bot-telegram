"""
Manejadores para las etapas iniciales de la conversación: selección de tipo de café y proveedor
"""
import logging
import traceback
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from utils.formatters import formatear_precio
from utils.sheets import get_all_data
from handlers.compra_mixta.config import (
    TIPO_CAFE, PROVEEDOR, CANTIDAD, 
    TIPOS_CAFE, datos_compra_mixta, debug_log
)
from handlers.compra_mixta.utils import obtener_proveedores_con_adelantos

logger = logging.getLogger(__name__)

async def compra_mixta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de compra con múltiples métodos de pago"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        logger.info(f"=== COMANDO /compra_mixta INICIADO por {username} (ID: {user_id}) ===")
        
        # Inicializar datos para este usuario
        datos_compra_mixta[user_id] = {
            "registrado_por": username,
            "monto_efectivo": 0,
            "monto_transferencia": 0,
            "monto_adelanto": 0,
            "monto_por_pagar": 0,
            "adelanto_id": ""
        }
        
        # Pre-cargar la lista de proveedores con adelantos para tenerla ya disponible
        # y evitar problemas de timing
        try:
            proveedores_adelantos = obtener_proveedores_con_adelantos()
            datos_compra_mixta[user_id]["proveedores_con_adelanto"] = proveedores_adelantos
            debug_log(f"Pre-cargados {len(proveedores_adelantos)} proveedores con adelanto para el usuario {user_id}")
        except Exception as e:
            debug_log(f"Error al pre-cargar proveedores: {e}")
            # Si hay error, continuar con una lista vacía
            datos_compra_mixta[user_id]["proveedores_con_adelanto"] = set()
        
        # Crear teclado con las 3 opciones predefinidas para tipo de café
        keyboard = [[tipo] for tipo in TIPOS_CAFE]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "🛒 *COMPRA CON PAGOS MIXTOS*\n\n"
            "Este tipo de compra te permite utilizar diferentes formas de pago:\n"
            "- Efectivo\n"
            "- Transferencia\n"
            "- Adelantos existentes\n"
            "- Por pagar\n"
            "- O combinaciones de estos métodos\n\n"
            "Selecciona el tipo de café:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return TIPO_CAFE
    except Exception as e:
        logger.error(f"Error en compra_mixta_command: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al iniciar el comando. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def tipo_cafe_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el tipo de café y solicitar el proveedor"""
    try:
        user_id = update.effective_user.id
        selected_tipo = update.message.text.strip().upper()
        
        # Verificar que sea uno de los tipos permitidos
        if selected_tipo not in TIPOS_CAFE:
            # Si no es un tipo válido, volver a mostrar las opciones
            keyboard = [[tipo] for tipo in TIPOS_CAFE]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                f"❌ Tipo de café no válido. Por favor, selecciona una de las opciones disponibles:",
                reply_markup=reply_markup
            )
            return TIPO_CAFE
        
        # Guardar el tipo de café
        logger.info(f"Usuario {user_id} seleccionó tipo de café: {selected_tipo}")
        datos_compra_mixta[user_id]["tipo_cafe"] = selected_tipo
        
        # Obtener lista de proveedores con adelantos disponibles
        # Primero verificar si ya tenemos la lista pre-cargada
        proveedores_con_adelanto = datos_compra_mixta[user_id].get("proveedores_con_adelanto", None)
        if proveedores_con_adelanto is None:
            debug_log(f"Lista de proveedores no pre-cargada para usuario {user_id}, obteniendo ahora...")
            try:
                proveedores_con_adelanto = obtener_proveedores_con_adelantos()
                datos_compra_mixta[user_id]["proveedores_con_adelanto"] = proveedores_con_adelanto
            except Exception as e:
                debug_log(f"Error al obtener proveedores: {e}")
                # Si hay error, usar una lista vacía
                proveedores_con_adelanto = set()
                datos_compra_mixta[user_id]["proveedores_con_adelanto"] = proveedores_con_adelanto
        
        debug_log(f"Mostrando lista de {len(proveedores_con_adelanto)} proveedores al usuario {user_id}")
        
        if proveedores_con_adelanto:
            # Crear teclado con los proveedores que tienen adelantos
            keyboard = [[proveedor] for proveedor in sorted(list(proveedores_con_adelanto))]
            keyboard.append(["Otro proveedor"])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            # Log de los proveedores encontrados
            debug_log(f"Creado teclado con proveedores: {[k[0] for k in keyboard]}")
            
            await update.message.reply_text(
                f"☕ Tipo de café: {selected_tipo}\n\n"
                "📋 *PROVEEDORES CON ADELANTOS DISPONIBLES:*\n"
                "Selecciona un proveedor o escribe uno nuevo:",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return PROVEEDOR
        else:
            # Si no hay proveedores con adelantos, continuar con flujo normal
            debug_log("No se encontraron proveedores con adelantos disponibles, mostrando flujo normal")
            await update.message.reply_text(
                f"☕ Tipo de café: {selected_tipo}\n\n"
                "Ahora, ingresa el nombre del proveedor:",
                reply_markup=ReplyKeyboardRemove()
            )
            return PROVEEDOR
    except Exception as e:
        logger.error(f"Error en tipo_cafe_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar tu selección. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END

async def proveedor_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el proveedor y solicitar la cantidad"""
    try:
        user_id = update.effective_user.id
        proveedor_texto = update.message.text.strip()
        
        # Verificar si el usuario seleccionó "Otro proveedor"
        if proveedor_texto == "Otro proveedor":
            debug_log(f"Usuario {user_id} seleccionó 'Otro proveedor'")
            await update.message.reply_text(
                "Escribe el nombre del proveedor:",
                reply_markup=ReplyKeyboardRemove()
            )
            return PROVEEDOR
        
        # Verificar que no esté vacío
        if not proveedor_texto:
            await update.message.reply_text(
                "❌ Por favor, ingresa un nombre de proveedor válido."
            )
            return PROVEEDOR
        
        logger.info(f"Usuario {user_id} ingresó proveedor: {proveedor_texto}")
        datos_compra_mixta[user_id]["proveedor"] = proveedor_texto
        
        # Verificar si este proveedor tiene adelantos disponibles y guardarlo para más tarde
        try:
            adelantos = get_all_data("adelantos")
            debug_log(f"Verificando adelantos para {proveedor_texto} - Encontrados {len(adelantos)} adelantos en total")
            
            # Filtrar adelantos del proveedor con saldo
            adelantos_proveedor = []
            for adelanto in adelantos:
                if adelanto.get('proveedor') == proveedor_texto:
                    try:
                        # Extraer y validar el saldo
                        saldo_str = adelanto.get('saldo_restante', '0')
                        try:
                            saldo = 0
                            if saldo_str:
                                saldo = float(str(saldo_str).replace(',', '.'))
                        except (ValueError, TypeError):
                            debug_log(f"Error al convertir saldo_restante: '{saldo_str}'")
                            saldo = 0
                        
                        debug_log(f"Adelanto encontrado para {proveedor_texto} con saldo {saldo}")
                        if saldo > 0:
                            adelantos_proveedor.append(adelanto)
                            debug_log(f"Añadido adelanto con saldo {saldo} para {proveedor_texto}")
                    except Exception as e:
                        debug_log(f"Error procesando saldo: {e}")
                        continue
            
            # Calcular saldo total y guardar adelantos
            if adelantos_proveedor:
                # Calcular el saldo total con validación explícita
                saldo_total = 0
                for adelanto in adelantos_proveedor:
                    saldo_str = adelanto.get('saldo_restante', '0')
                    try:
                        if saldo_str:
                            saldo = float(str(saldo_str).replace(',', '.'))
                            saldo_total += saldo
                    except (ValueError, TypeError):
                        debug_log(f"Error al sumar saldo_restante: '{saldo_str}'")
                
                datos_compra_mixta[user_id]["tiene_adelantos"] = True
                datos_compra_mixta[user_id]["adelantos_disponibles"] = adelantos_proveedor
                datos_compra_mixta[user_id]["saldo_adelantos"] = saldo_total
                
                debug_log(f"El proveedor {proveedor_texto} tiene {len(adelantos_proveedor)} adelantos con saldo total {saldo_total}")
                
                await update.message.reply_text(
                    f"ℹ️ El proveedor {proveedor_texto} tiene adelantos vigentes "
                    f"por un total de {formatear_precio(saldo_total)}."
                )
            else:
                datos_compra_mixta[user_id]["tiene_adelantos"] = False
                debug_log(f"El proveedor {proveedor_texto} no tiene adelantos con saldo")
                
                # Si el usuario seleccionó un proveedor de la lista pero no tiene adelantos
                # (Esto podría pasar si los saldos cambiaron entre la carga de la lista y la selección)
                proveedores_con_adelanto = datos_compra_mixta[user_id].get("proveedores_con_adelanto", set())
                if proveedor_texto in proveedores_con_adelanto:
                    await update.message.reply_text(
                        f"⚠️ El proveedor {proveedor_texto} ya no tiene adelantos disponibles."
                    )
        except Exception as e:
            debug_log(f"Error al verificar adelantos del proveedor: {e}")
            debug_log(traceback.format_exc())
            datos_compra_mixta[user_id]["tiene_adelantos"] = False
        
        await update.message.reply_text(
            f"👨‍🌾 Proveedor: {proveedor_texto}\n\n"
            "Ahora, ingresa la cantidad de café en kg:"
        )
        return CANTIDAD
    except Exception as e:
        logger.error(f"Error en proveedor_step: {e}")
        logger.error(traceback.format_exc())
        
        # Responder al usuario incluso si hay error
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar el proveedor. Por favor, intenta nuevamente."
        )
        return ConversationHandler.END
