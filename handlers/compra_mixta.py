import logging
import traceback
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, ConversationHandler, 
    MessageHandler, filters, CallbackQueryHandler
)

from utils.sheets import append_data as append_sheets, generate_unique_id, get_all_data, get_filtered_data
from utils.helpers import get_now_peru, safe_float, format_date_for_sheets, format_currency, calculate_total
from utils.formatters import formatear_numero, formatear_precio, procesar_entrada_numerica
from utils.sheets.almacen import update_almacen

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
TIPO_CAFE, PROVEEDOR, CANTIDAD, PRECIO, METODO_PAGO, MONTO_EFECTIVO, MONTO_TRANSFERENCIA, SELECCIONAR_ADELANTO, CONFIRMAR = range(9)

# Tipos de café predefinidos - solo 3 opciones fijas (copiado de compras.py)
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

# Headers para la hoja de compras mixtas
COMPRAS_MIXTAS_HEADERS = [
    "id", "fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "preciototal", 
    "metodo_pago", "monto_efectivo", "monto_transferencia", "monto_adelanto", 
    "adelanto_id", "registrado_por", "notas"
]

# Función para obtener proveedores con adelantos
def obtener_proveedores_con_adelantos():
    """
    Obtiene una lista de proveedores que tienen adelantos con saldo disponible
    
    Returns:
        set: Conjunto de nombres de proveedores con adelantos disponibles
    """
    try:
        logger.info("Obteniendo lista de proveedores con adelantos disponibles")
        adelantos = get_all_data("adelantos")
        
        # Obtener proveedores únicos con saldo > 0
        proveedores_con_adelanto = set()
        for adelanto in adelantos:
            try:
                saldo = float(adelanto.get('saldo_restante', 0))
                if saldo > 0:
                    proveedor = adelanto.get('proveedor', '')
                    if proveedor:
                        proveedores_con_adelanto.add(proveedor)
            except (ValueError, TypeError):
                continue
        
        logger.info(f"Se encontraron {len(proveedores_con_adelanto)} proveedores con adelantos disponibles")
        return proveedores_con_adelanto
    except Exception as e:
        logger.error(f"Error al obtener proveedores con adelantos: {e}")
        return set()

async def compra_mixta_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de compra con múltiples métodos de pago"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /compra_mixta INICIADO por {username} (ID: {user_id}) ===")
    
    # Inicializar datos para este usuario
    datos_compra_mixta[user_id] = {
        "registrado_por": username,
        "monto_efectivo": 0,
        "monto_transferencia": 0,
        "monto_adelanto": 0,
        "adelanto_id": ""
    }
    
    # Crear teclado con las 3 opciones predefinidas para tipo de café
    keyboard = [[tipo] for tipo in TIPOS_CAFE]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "🛒 *COMPRA CON PAGOS MIXTOS*\n\n"
        "Este tipo de compra te permite utilizar diferentes formas de pago:\n"
        "- Efectivo\n"
        "- Transferencia\n"
        "- Adelantos existentes\n"
        "- O combinaciones de estos métodos\n\n"
        "Selecciona el tipo de café:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    return TIPO_CAFE

async def tipo_cafe_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el tipo de café y solicitar el proveedor"""
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
    proveedores_con_adelanto = obtener_proveedores_con_adelantos()
    
    if proveedores_con_adelanto:
        # Crear teclado con los proveedores que tienen adelantos
        keyboard = [[proveedor] for proveedor in sorted(list(proveedores_con_adelanto))]
        keyboard.append(["Otro proveedor"])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        # Guardar la lista de proveedores con adelantos para usarla después
        datos_compra_mixta[user_id]["proveedores_con_adelanto"] = proveedores_con_adelanto
        
        # Log de los proveedores encontrados
        logger.info(f"Mostrando lista de proveedores con adelantos: {proveedores_con_adelanto}")
        
        await update.message.reply_text(
            f"☕ Tipo de café: {selected_tipo}\n\n"
            "📋 Proveedores con adelantos disponibles:\n"
            "Selecciona un proveedor o escribe uno nuevo:",
            reply_markup=reply_markup
        )
        return PROVEEDOR
    else:
        # Si no hay proveedores con adelantos, continuar con flujo normal
        logger.info("No se encontraron proveedores con adelantos disponibles")
        await update.message.reply_text(
            f"☕ Tipo de café: {selected_tipo}\n\n"
            "Ahora, ingresa el nombre del proveedor:",
            reply_markup=ReplyKeyboardRemove()
        )
        return PROVEEDOR

async def proveedor_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el proveedor y solicitar la cantidad"""
    user_id = update.effective_user.id
    proveedor_texto = update.message.text.strip()
    
    # Verificar si el usuario seleccionó "Otro proveedor"
    if proveedor_texto == "Otro proveedor":
        logger.info(f"Usuario {user_id} seleccionó 'Otro proveedor'")
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
        
        # Filtrar adelantos del proveedor con saldo
        adelantos_proveedor = []
        for adelanto in adelantos:
            if adelanto.get('proveedor') == proveedor_texto:
                try:
                    saldo = float(adelanto.get('saldo_restante', 0))
                    if saldo > 0:
                        adelantos_proveedor.append(adelanto)
                except (ValueError, TypeError):
                    continue
        
        # Calcular saldo total y guardar adelantos
        if adelantos_proveedor:
            saldo_total = sum(float(adelanto.get('saldo_restante', 0)) for adelanto in adelantos_proveedor)
            datos_compra_mixta[user_id]["tiene_adelantos"] = True
            datos_compra_mixta[user_id]["adelantos_disponibles"] = adelantos_proveedor
            datos_compra_mixta[user_id]["saldo_adelantos"] = saldo_total
            
            await update.message.reply_text(
                f"ℹ️ El proveedor {proveedor_texto} tiene adelantos vigentes "
                f"por un total de {formatear_precio(saldo_total)}."
            )
        else:
            datos_compra_mixta[user_id]["tiene_adelantos"] = False
            
            # Si el usuario seleccionó un proveedor de la lista pero no tiene adelantos
            # (Esto podría pasar si los saldos cambiaron entre la carga de la lista y la selección)
            proveedores_con_adelanto = datos_compra_mixta[user_id].get("proveedores_con_adelanto", set())
            if proveedor_texto in proveedores_con_adelanto:
                await update.message.reply_text(
                    f"⚠️ El proveedor {proveedor_texto} ya no tiene adelantos disponibles."
                )
    except Exception as e:
        logger.error(f"Error al verificar adelantos del proveedor: {e}")
        logger.error(traceback.format_exc())
        datos_compra_mixta[user_id]["tiene_adelantos"] = False
    
    await update.message.reply_text(
        f"👨‍🌾 Proveedor: {proveedor_texto}\n\n"
        "Ahora, ingresa la cantidad de café en kg:"
    )
    return CANTIDAD

async def cantidad_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar la cantidad y solicitar el precio"""
    user_id = update.effective_user.id
    try:
        cantidad_text = update.message.text.strip()
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
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, ingresa un número válido para la cantidad."
        )
        return CANTIDAD

async def precio_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guardar el precio y solicitar método de pago"""
    user_id = update.effective_user.id
    try:
        precio_text = update.message.text.strip()
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
            metodos = METODOS_PAGO
        else:
            # Filtrar métodos que incluyen adelanto
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
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, ingresa un número válido para el precio."
        )
        return PRECIO

async def metodo_pago_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar el método de pago seleccionado y dirigir al flujo correspondiente"""
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

async def monto_efectivo_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar el monto en efectivo"""
    user_id = update.effective_user.id
    try:
        monto_text = update.message.text.strip()
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
    
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, ingresa un número válido para el monto en efectivo."
        )
        return MONTO_EFECTIVO

async def monto_transferencia_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar el monto por transferencia"""
    user_id = update.effective_user.id
    try:
        monto_text = update.message.text.strip()
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
    
    except ValueError:
        await update.message.reply_text(
            "❌ Por favor, ingresa un número válido para el monto por transferencia."
        )
        return MONTO_TRANSFERENCIA

async def seleccionar_adelanto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostrar adelantos disponibles para selección"""
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
        saldo = float(adelanto.get('saldo_restante', 0))
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

async def seleccionar_adelanto_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesar la selección de adelanto"""
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
        saldo = float(adelanto_seleccionado.get('saldo_restante', 0))
        
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
        
        # Mostrar resumen final
        return await mostrar_resumen(update, context)
    else:
        await query.edit_message_text("❌ Error al seleccionar el adelanto. Por favor, intenta nuevamente.")
        return ConversationHandler.END

async def mostrar_resumen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mostrar resumen de la compra y solicitar confirmación"""
    user_id = update.effective_user.id if update.message else update.callback_query.from_user.id
    
    # Obtener los datos de la compra
    datos = datos_compra_mixta[user_id]
    
    # Crear resumen
    resumen = "📋 *RESUMEN DE COMPRA MIXTA*\n\n"
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
    
    # Crear teclado para confirmación
    keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Enviar mensaje según el tipo de actualización
    if update.message:
        await update.message.reply_text(
            resumen + "\n¿Confirmas esta compra?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        # Si venimos de un callback, enviar un nuevo mensaje
        await context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text=resumen + "\n¿Confirmas esta compra?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    
    return CONFIRMAR

async def confirmar_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirmar y registrar la compra mixta"""
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
            if datos.get("monto_adelanto", 0) > 0 and datos.get("adelanto_id", ""):
                try:
                    from utils.sheets import update_cell
                    
                    # Calcular el nuevo saldo
                    nuevo_saldo = datos.get("adelanto_saldo", 0) - datos.get("monto_adelanto", 0)
                    
                    # Actualizar el saldo en la hoja de adelantos
                    update_cell("adelantos", datos["adelanto_id"], "saldo_restante", nuevo_saldo)
                    logger.info(f"Actualizado saldo de adelanto {datos['adelanto_id']} a {nuevo_saldo}")
                except Exception as e:
                    logger.error(f"Error al actualizar saldo de adelanto: {e}")
                    logger.error(traceback.format_exc())
            
            # 1. Guardar la compra en la hoja de compras_mixtas
            logger.info(f"Guardando compra mixta en Google Sheets: {datos}")
            result_mixta = append_sheets("compras_mixtas", datos)
            
            # 2. Guardar también en la hoja de compras regular
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
            
            # 3. Registrar en almacén
            logger.info(f"Registrando la compra en almacén")
            result_almacen = update_almacen(
                fase=datos["tipo_cafe"],
                cantidad_cambio=datos["cantidad"],
                operacion="sumar",
                notas=f"Compra mixta ID: {compra_id}",
                compra_id=compra_id
            )
            
            if result_mixta and result_compra:
                logger.info(f"Compra mixta guardada exitosamente para usuario {user_id}")
                
                # Mensaje de éxito
                mensaje_exito = "✅ *¡COMPRA MIXTA REGISTRADA EXITOSAMENTE!*\n\n"
                mensaje_exito += f"ID: {datos['id']}\n"
                mensaje_exito += f"Proveedor: {datos['proveedor']}\n"
                mensaje_exito += f"Total: {formatear_precio(datos['preciototal'])}\n\n"
                
                # Añadir información sobre almacén
                if result_almacen:
                    mensaje_exito += "✅ Registrado en almacén correctamente\n\n"
                else:
                    mensaje_exito += "⚠️ La compra se registró pero hubo un error al actualizar el almacén\n\n"
                
                mensaje_exito += "Usa /compra_mixta para registrar otra compra."
                
                await update.message.reply_text(
                    mensaje_exito,
                    parse_mode="Markdown",
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

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancelar la conversación"""
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

def register_compra_mixta_handlers(application):
    """Registra los handlers para el módulo de compra mixta"""
    logger.info("Registrando handlers para compra mixta")
    
    # Crear manejador de conversación
    compra_mixta_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("compra_mixta", compra_mixta_command)],
        states={
            TIPO_CAFE: [MessageHandler(filters.TEXT & ~filters.COMMAND, tipo_cafe_step)],
            PROVEEDOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, proveedor_step)],
            CANTIDAD: [MessageHandler(filters.TEXT & ~filters.COMMAND, cantidad_step)],
            PRECIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, precio_step)],
            METODO_PAGO: [MessageHandler(filters.TEXT & ~filters.COMMAND, metodo_pago_step)],
            MONTO_EFECTIVO: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_efectivo_step)],
            MONTO_TRANSFERENCIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, monto_transferencia_step)],
            SELECCIONAR_ADELANTO: [CallbackQueryHandler(seleccionar_adelanto_callback, pattern=r'^adelanto_')],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_step)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
        # Añadir opción para permitir que se caigan las conversaciones después de cierto tiempo de inactividad
        conversation_timeout=900  # 15 minutos - para evitar conversaciones colgadas
    )
    
    # Agregar el manejador a la aplicación
    application.add_handler(compra_mixta_conv_handler)
    logger.info("Handlers de compra mixta registrados correctamente")
    
    return True