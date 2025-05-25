"""
Manejador para el comando /evidencia.
Este comando permite seleccionar una operación (compra, venta, adelanto o gasto) y subir una evidencia.
"""

import logging
import os
import uuid
import traceback
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from utils.sheets import get_all_data, append_data as append_sheets, generate_unique_id, get_filtered_data
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive, setup_drive_folders
from config import UPLOADS_FOLDER, DRIVE_ENABLED, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID, DRIVE_EVIDENCIAS_ROOT_ID

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_TIPO, SELECCIONAR_OPERACION, SELECCIONAR_GASTOS, SUBIR_DOCUMENTO, CONFIRMAR = range(5)

# Datos temporales
datos_evidencia = {}

# Número máximo de operaciones a mostrar
MAX_OPERACIONES = 10

# Asegurar que existe el directorio de uploads
if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)
    logger.info(f"Directorio de uploads creado: {UPLOADS_FOLDER}")

# Asegurar que existen los directorios para cada tipo de operación
COMPRAS_FOLDER = os.path.join(UPLOADS_FOLDER, "compras")
VENTAS_FOLDER = os.path.join(UPLOADS_FOLDER, "ventas")
ADELANTOS_FOLDER = os.path.join(UPLOADS_FOLDER, "adelantos")
GASTOS_FOLDER = os.path.join(UPLOADS_FOLDER, "gastos")

if not os.path.exists(COMPRAS_FOLDER):
    os.makedirs(COMPRAS_FOLDER)
    logger.info(f"Directorio para evidencias de compras creado: {COMPRAS_FOLDER}")

if not os.path.exists(VENTAS_FOLDER):
    os.makedirs(VENTAS_FOLDER)
    logger.info(f"Directorio para evidencias de ventas creado: {VENTAS_FOLDER}")

if not os.path.exists(ADELANTOS_FOLDER):
    os.makedirs(ADELANTOS_FOLDER)
    logger.info(f"Directorio para evidencias de adelantos creado: {ADELANTOS_FOLDER}")

if not os.path.exists(GASTOS_FOLDER):
    os.makedirs(GASTOS_FOLDER)
    logger.info(f"Directorio para evidencias de gastos creado: {GASTOS_FOLDER}")

# Verificar la configuración de Google Drive al cargar el módulo
if DRIVE_ENABLED:
    logger.info("Google Drive está habilitado. Verificando estructura de carpetas...")
    # Verificar que los IDs de carpetas estén configurados, o crearlos si no existen
    if not (DRIVE_EVIDENCIAS_ROOT_ID and DRIVE_EVIDENCIAS_COMPRAS_ID and DRIVE_EVIDENCIAS_VENTAS_ID):
        logger.warning("IDs de carpetas de Drive no encontrados. Intentando configurar estructura de carpetas...")
        setup_result = setup_drive_folders()
        if setup_result:
            logger.info("Estructura de carpetas en Drive configurada correctamente")
        else:
            logger.error("No se pudo configurar la estructura de carpetas en Drive")
    else:
        logger.info("IDs de carpetas de Drive verificados correctamente")
else:
    logger.info("Google Drive está deshabilitado. Se usará almacenamiento local.")

async def evidencia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Comando /evidencia para seleccionar el tipo de operación
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /evidencia INICIADO por {username} (ID: {user_id}) ===")
    
    # Inicializar datos para este usuario
    datos_evidencia[user_id] = {
        "registrado_por": update.effective_user.username or update.effective_user.first_name,
        "gastos_seleccionados": []  # Lista para almacenar múltiples gastos seleccionados
    }
    
    # Ofrecer opciones para los diferentes tipos de operaciones
    keyboard = [
        ["🛒 Compras"],
        ["💰 Ventas"],
        ["💸 Adelantos"],
        ["📊 Gastos"],
        ["❌ Cancelar"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    mensaje = "📋 *SELECCIONA EL TIPO DE OPERACIÓN*\n\n"
    mensaje += "Elige para qué tipo de operación quieres registrar evidencia."
    
    await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
    
    # Pasar al estado de selección de tipo
    return SELECCIONAR_TIPO

async def seleccionar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección del tipo de operación por el usuario"""
    user_id = update.effective_user.id
    respuesta = update.message.text.strip()
    
    # Verificar si el usuario cancela
    if respuesta.lower() == "❌ cancelar":
        await update.message.reply_text("Operación cancelada. Usa /evidencia para iniciar nuevamente.")
        return ConversationHandler.END
    
    # Determinar el tipo de operación
    if "compras" in respuesta.lower():
        tipo_operacion = "COMPRA"
        operacion_plural = "compras"
        datos_evidencia[user_id]["tipo_operacion"] = tipo_operacion
        datos_evidencia[user_id]["folder_name"] = "compras"  # Guardar el nombre de la carpeta
        logger.info(f"Usuario {user_id} seleccionó tipo de operación: {tipo_operacion}")
    elif "ventas" in respuesta.lower():
        tipo_operacion = "VENTA"
        operacion_plural = "ventas"
        datos_evidencia[user_id]["tipo_operacion"] = tipo_operacion
        datos_evidencia[user_id]["folder_name"] = "ventas"  # Guardar el nombre de la carpeta
        logger.info(f"Usuario {user_id} seleccionó tipo de operación: {tipo_operacion}")
    elif "adelantos" in respuesta.lower():
        tipo_operacion = "ADELANTO"
        operacion_plural = "adelantos"
        datos_evidencia[user_id]["tipo_operacion"] = tipo_operacion
        datos_evidencia[user_id]["folder_name"] = "adelantos"  # Guardar el nombre de la carpeta
        logger.info(f"Usuario {user_id} seleccionó tipo de operación: {tipo_operacion}")
    elif "gastos" in respuesta.lower():
        tipo_operacion = "GASTO"
        operacion_plural = "gastos"
        datos_evidencia[user_id]["tipo_operacion"] = tipo_operacion
        datos_evidencia[user_id]["folder_name"] = "gastos"  # Guardar el nombre de la carpeta
        logger.info(f"Usuario {user_id} seleccionó tipo de operación: {tipo_operacion}")
    else:
        await update.message.reply_text(
            "❌ Opción no válida. Por favor, selecciona una de las opciones disponibles.",
            parse_mode="Markdown"
        )
        return SELECCIONAR_TIPO
    
    # Mostrar las operaciones en un teclado seleccionable
    try:
        # Obtener datos según el tipo de operación seleccionado
        operaciones = get_all_data(operacion_plural)
        
        if operaciones:
            # Ordenar las operaciones por fecha (más recientes primero)
            operaciones_recientes = sorted(operaciones, key=lambda x: x.get('fecha', ''), reverse=True)
            
            # Limitar a las últimas operaciones para el teclado
            operaciones_recientes = operaciones_recientes[:MAX_OPERACIONES]
            
            # Para gastos usamos un enfoque diferente: selección múltiple con teclado inline
            if tipo_operacion == "GASTO":
                # Guardar las operaciones en context.user_data para usarlas en el callback
                context.user_data["gastos_disponibles"] = operaciones_recientes
                
                # Crear mensaje con la lista de gastos disponibles
                mensaje = "📊 *SELECCIÓN DE GASTOS*\n\n"
                mensaje += "Puedes seleccionar uno o varios gastos para una misma evidencia.\n\n"
                mensaje += "Gastos disponibles:\n"
                
                # Crear teclado inline para selección múltiple
                keyboard = []
                for i, gasto in enumerate(operaciones_recientes):
                    concepto = gasto.get('concepto', 'Sin descripción')
                    monto = gasto.get('monto', '0')
                    fecha = gasto.get('fecha', 'Fecha desconocida')
                    gasto_id = gasto.get('id', f'gasto_{i}')
                    
                    # Mostrar información resumida del gasto
                    mensaje += f"• {concepto} - S/ {monto} ({fecha})\n"
                    
                    # Añadir botón para seleccionar este gasto
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{concepto} - S/ {monto}",
                            callback_data=f"select_gasto_{gasto_id}"
                        )
                    ])
                
                # Botones para finalizar selección o cancelar
                keyboard.append([
                    InlineKeyboardButton("✅ Finalizar selección", callback_data="gastos_finalizar"),
                    InlineKeyboardButton("❌ Cancelar", callback_data="gastos_cancelar")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    mensaje,
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
                
                return SELECCIONAR_GASTOS
            
            # Para el resto de operaciones, mostrar teclado normal
            keyboard = []
            for operacion in operaciones_recientes:
                operacion_id = operacion.get('id', 'Sin ID')
                
                if tipo_operacion == "COMPRA":
                    # Mejorar formato: fecha, proveedor, monto y tipo de café
                    proveedor = operacion.get('proveedor', 'Proveedor desconocido')
                    tipo_cafe = operacion.get('tipo_cafe', 'Tipo desconocido')
                    total = operacion.get('preciototal', '0')
                    fecha = operacion.get('fecha', '').split(' ')[0]  # Solo mostrar fecha sin hora
                    boton_text = f"{fecha} | {proveedor} | S/ {total} | ID:{operacion_id}"
                elif tipo_operacion == "VENTA":
                    # Para ventas, mejorar el formato también
                    cliente = operacion.get('cliente', 'Cliente desconocido')
                    total = operacion.get('total', '0')
                    fecha = operacion.get('fecha', '').split(' ')[0]
                    boton_text = f"{fecha} | {cliente} | S/ {total} | ID:{operacion_id}"
                elif tipo_operacion == "ADELANTO":
                    # Para adelantos, mejorar también
                    proveedor = operacion.get('proveedor', 'Proveedor desconocido')
                    monto = operacion.get('monto', '0')
                    fecha = operacion.get('fecha', '').split(' ')[0]
                    boton_text = f"{fecha} | {proveedor} | S/ {monto} | ID:{operacion_id}"
                
                keyboard.append([boton_text])
            
            keyboard.append(["❌ Cancelar"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            total_operaciones = len(operaciones)
            mensaje = f"📋 *SELECCIONA UNA {tipo_operacion} PARA ADJUNTAR EVIDENCIA*\n\n"
            
            # Indicar cuántas operaciones se están mostrando de un total
            if total_operaciones > MAX_OPERACIONES:
                mensaje += f"Mostrando las {MAX_OPERACIONES} {operacion_plural} más recientes de un total de {total_operaciones}"
            else:
                mensaje += f"Mostrando {total_operaciones} {operacion_plural} disponibles"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
            
            # Redirigir al estado de selección de operación
            return SELECCIONAR_OPERACION
        else:
            comando_registro = f"/{operacion_plural[:-1]}"  # /compra, /venta, /adelanto, /gasto
            await update.message.reply_text(
                f"No hay {operacion_plural} registradas. Usa {comando_registro} para registrar una nueva operación.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error al obtener {operacion_plural}: {e}")
        await update.message.reply_text(
            f"❌ Ocurrió un error al obtener las {operacion_plural}. Por favor, intenta nuevamente.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

async def handle_gasto_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja la selección de gastos múltiples"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    callback_data = query.data
    
    # Si el usuario cancela
    if callback_data == "gastos_cancelar":
        await query.message.reply_text(
            "Operación cancelada. Usa /evidencia para iniciar nuevamente.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Si el usuario finaliza la selección
    if callback_data == "gastos_finalizar":
        # Verificar si hay al menos un gasto seleccionado
        if not datos_evidencia[user_id]["gastos_seleccionados"]:
            await query.message.reply_text(
                "⚠️ Debes seleccionar al menos un gasto antes de finalizar.",
                parse_mode="Markdown"
            )
            return SELECCIONAR_GASTOS
        
        # Construir mensaje de resumen
        mensaje = "📊 *GASTOS SELECCIONADOS*\n\n"
        
        total_monto = 0
        for gasto_id in datos_evidencia[user_id]["gastos_seleccionados"]:
            # Buscar el gasto en la lista de gastos disponibles
            for gasto in context.user_data.get("gastos_disponibles", []):
                if gasto.get('id') == gasto_id:
                    concepto = gasto.get('concepto', 'Sin descripción')
                    monto = float(gasto.get('monto', 0))
                    mensaje += f"• {concepto} - S/ {monto}\n"
                    total_monto += monto
        
        mensaje += f"\nTotal: S/ {total_monto}\n\n"
        mensaje += "Ahora, envía la imagen de la evidencia.\n"
        mensaje += "La imagen debe ser clara y legible."
        
        # Almacenar el monto total para usarlo después
        datos_evidencia[user_id]["monto"] = str(total_monto)
        
        # Convertir los IDs de gastos a una cadena única para usar como operacion_id
        datos_evidencia[user_id]["operacion_id"] = "+".join(datos_evidencia[user_id]["gastos_seleccionados"])
        
        # Modo de almacenamiento
        almacenamiento = "Google Drive" if DRIVE_ENABLED else "almacenamiento local"
        mensaje += f"\n\nNota: La imagen se guardará en {almacenamiento}."
        
        await query.message.reply_text(mensaje, parse_mode="Markdown")
        return SUBIR_DOCUMENTO
    
    # Si el usuario selecciona un gasto
    if callback_data.startswith("select_gasto_"):
        gasto_id = callback_data.replace("select_gasto_", "")
        
        # Alternar selección (añadir o quitar de la lista)
        if gasto_id in datos_evidencia[user_id]["gastos_seleccionados"]:
            datos_evidencia[user_id]["gastos_seleccionados"].remove(gasto_id)
            await query.message.reply_text(f"Gasto con ID {gasto_id} eliminado de la selección.")
        else:
            datos_evidencia[user_id]["gastos_seleccionados"].append(gasto_id)
            await query.message.reply_text(f"Gasto con ID {gasto_id} añadido a la selección.")
        
        # Mostrar selección actual
        seleccionados = len(datos_evidencia[user_id]["gastos_seleccionados"])
        await query.message.reply_text(f"Tienes {seleccionados} gastos seleccionados. Usa 'Finalizar selección' cuando termines.")
        
        return SELECCIONAR_GASTOS

async def seleccionar_operacion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de la operación por el usuario"""
    user_id = update.effective_user.id
    respuesta = update.message.text.strip()
    
    # Verificar si el usuario cancela
    if respuesta.lower() == "❌ cancelar":
        await update.message.reply_text("Operación cancelada. Usa /evidencia para iniciar nuevamente.")
        return ConversationHandler.END
    
    # Extraer el ID de la operación (ahora está después de "ID:")
    if "ID:" in respuesta:
        operacion_id = respuesta.split("ID:")[1].strip()
    else:
        # Mantener comportamiento anterior como fallback
        partes = respuesta.split(',')
        if len(partes) < 3:
            await update.message.reply_text(
                "❌ Formato de selección inválido. Por favor, usa /evidencia para intentar nuevamente.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        operacion_id = partes[-1].strip()
    
    tipo_operacion = datos_evidencia[user_id]["tipo_operacion"]
    logger.info(f"Usuario {user_id} seleccionó {tipo_operacion} con ID: {operacion_id}")
    
    # Guardar los datos de la operación
    datos_evidencia[user_id]["operacion_id"] = operacion_id
    
    # Guardar información adicional sobre la operación
    operacion_sheet = datos_evidencia[user_id]["folder_name"]  # compras, ventas, adelantos
    operacion_data = get_filtered_data(operacion_sheet, {"id": operacion_id})
    
    if operacion_data and len(operacion_data) > 0:
        # Guardar el monto para usarlo en el nombre del archivo según el tipo de operación
        if tipo_operacion == "COMPRA":
            monto = operacion_data[0].get('preciototal', '0')
        elif tipo_operacion == "VENTA":
            monto = operacion_data[0].get('total', '0')
        elif tipo_operacion == "ADELANTO":
            monto = operacion_data[0].get('monto', '0')
        else:
            monto = '0'
        
        # Limpiar el monto (quitar caracteres no numéricos excepto punto)
        monto_limpio = ''.join(c for c in str(monto) if c.isdigit() or c == '.')
        if not monto_limpio:
            monto_limpio = '0'  # Si quedó vacío, usar '0'
            
        datos_evidencia[user_id]["monto"] = monto_limpio
        logger.info(f"Monto para {tipo_operacion} {operacion_id}: S/ {monto_limpio}")
    else:
        # Si no se encuentra la operación, usar '0' como valor predeterminado
        datos_evidencia[user_id]["monto"] = '0'
        logger.warning(f"No se encontró información para {tipo_operacion} {operacion_id}")
    
    # Modo de almacenamiento
    almacenamiento = "Google Drive" if DRIVE_ENABLED else "almacenamiento local"
    
    # Informar al usuario que se ha seleccionado correctamente la operación
    await update.message.reply_text(
        f"Has seleccionado la {tipo_operacion} con ID: {operacion_id}\n\n"
        f"Ahora, envía la imagen de la evidencia.\n"
        f"La imagen debe ser clara y legible.\n\n"
        f"Nota: La imagen se guardará en {almacenamiento}."
    )
    
    # Pasar al siguiente estado
    return SUBIR_DOCUMENTO

async def subir_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el documento cargado"""
    user_id = update.effective_user.id
    
    # Verificar si el mensaje contiene una foto
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Por favor, envía una imagen de la evidencia.\n"
            "Si deseas cancelar, usa el comando /cancelar."
        )
        return SUBIR_DOCUMENTO
    
    # Obtener la foto de mejor calidad (la última en la lista)
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    logger.info(f"Usuario {user_id} subió imagen con file_id: {file_id}")
    
    # Guardar información de la foto
    datos_evidencia[user_id]["archivo_id"] = file_id
    
    # Obtener el archivo
    file = await context.bot.get_file(file_id)
    
    # Crear un nombre único para el archivo incluyendo el monto y la información relevante según el tipo de operación
    tipo_op = datos_evidencia[user_id]["tipo_operacion"].lower()
    op_id = datos_evidencia[user_id]["operacion_id"]
    monto = datos_evidencia[user_id]["monto"]
    
    # Obtener información adicional según el tipo de operación
    operacion_sheet = datos_evidencia[user_id]["folder_name"]  # compras, ventas, adelantos, gastos
    operacion_data = get_filtered_data(operacion_sheet, {"id": op_id})
    
    # Información adicional para el nombre del archivo
    info_adicional = ""
    
    # Para gastos múltiples, usar un identificador único en lugar de todos los IDs
    if tipo_op.upper() == "GASTO" and "+" in op_id:
        gasto_count = len(op_id.split("+"))
        
        # Intentar obtener el concepto del primer gasto
        primero_id = op_id.split("+")[0]
        gasto_data = get_filtered_data("gastos", {"id": primero_id})
        if gasto_data and len(gasto_data) > 0:
            concepto = gasto_data[0].get('concepto', '').replace(' ', '_')[:20]
            info_adicional = f"concepto-{concepto}"
        
        nombre_archivo = f"{tipo_op}_multiple_{gasto_count}_gastos_{info_adicional}_S{monto}_{uuid.uuid4().hex[:8]}.jpg"
    else:
        # Obtener información específica según el tipo de operación
        if operacion_data and len(operacion_data) > 0:
            if tipo_op.upper() == "COMPRA":
                # Para compras, incluir el nombre del proveedor
                proveedor = operacion_data[0].get('proveedor', '').replace(' ', '_')[:20]
                info_adicional = f"prov-{proveedor}"
            elif tipo_op.upper() == "VENTA":
                # Para ventas, incluir el nombre del cliente
                cliente = operacion_data[0].get('cliente', '').replace(' ', '_')[:20]
                info_adicional = f"cli-{cliente}"
            elif tipo_op.upper() == "GASTO":
                # Para gastos individuales, incluir el concepto
                concepto = operacion_data[0].get('concepto', '').replace(' ', '_')[:20]
                info_adicional = f"concepto-{concepto}"
            elif tipo_op.upper() == "ADELANTO":
                # Para adelantos, incluir el nombre del proveedor
                proveedor = operacion_data[0].get('proveedor', '').replace(' ', '_')[:20]
                info_adicional = f"prov-{proveedor}"
        
        # Añadir información adicional al nombre del archivo
        if info_adicional:
            nombre_archivo = f"{tipo_op}_{op_id}_{info_adicional}_S{monto}_{uuid.uuid4().hex[:8]}.jpg"
        else:
            nombre_archivo = f"{tipo_op}_{op_id}_S{monto}_{uuid.uuid4().hex[:8]}.jpg"
    
    # Guardar el nombre del archivo
    datos_evidencia[user_id]["nombre_archivo"] = nombre_archivo
    
    # Determinar la carpeta local según el tipo de operación
    folder_name = datos_evidencia[user_id]["folder_name"]
    local_folder = os.path.join(UPLOADS_FOLDER, folder_name)
    
    # Para Google Drive, usar la carpeta de compras por defecto si no hay una específica
    folder_id = None
    if DRIVE_ENABLED:
        if tipo_op.upper() == "COMPRA":
            folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID
        elif tipo_op.upper() == "VENTA":
            folder_id = DRIVE_EVIDENCIAS_VENTAS_ID
        else:
            # Para otros tipos, usar la carpeta de compras por defecto
            folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID
    
    logger.info(f"Evidencia de {tipo_op.upper()} - Se guardará en la carpeta: {local_folder}")
    
    # Siempre guardar una copia local primero
    local_path = os.path.join(local_folder, nombre_archivo)
    await file.download_to_drive(local_path)
    logger.info(f"Archivo guardado localmente en: {local_path}")
    datos_evidencia[user_id]["ruta_archivo"] = os.path.join(folder_name, nombre_archivo)
    
    # Determinar si usar Google Drive además del almacenamiento local
    drive_file_info = None
    if DRIVE_ENABLED and folder_id:
        try:
            # Descargar el archivo a memoria para subir a Drive
            file_bytes = await file.download_as_bytearray()
            
            # Verificar que el folder_id es válido
            if not folder_id or folder_id.strip() == "":
                logger.error(f"ID de carpeta de Drive inválido: '{folder_id}'. Verificar configuración.")
                await update.message.reply_text(
                    "⚠️ Error en la configuración de Google Drive. Se usará solo almacenamiento local.",
                    parse_mode="Markdown"
                )
            else:
                # Subir el archivo a Drive
                logger.info(f"Iniciando subida a Drive en carpeta: {folder_id}")
                drive_file_info = upload_file_to_drive(file_bytes, nombre_archivo, "image/jpeg", folder_id)
                
                if drive_file_info and drive_file_info.get("id"):
                    # Guardar la información de Drive
                    datos_evidencia[user_id]["drive_file_id"] = drive_file_info.get("id")
                    datos_evidencia[user_id]["drive_view_link"] = drive_file_info.get("webViewLink")
                    logger.info(f"Archivo también subido a Drive: ID={drive_file_info.get('id')}, Enlace={drive_file_info.get('webViewLink')}")
                else:
                    logger.error("Error al subir archivo a Drive, usando solo almacenamiento local")
        except Exception as e:
            logger.error(f"Error al subir a Drive: {e}")
            logger.error(f"Detalles del error: {str(e)}")
            # Ya tenemos el archivo guardado localmente, así que continuamos
    
    # Preparar mensaje de confirmación
    tipo_operacion = datos_evidencia[user_id]["tipo_operacion"]
    
    # Para gastos múltiples, mostrar todos los IDs seleccionados
    if tipo_operacion == "GASTO" and "gastos_seleccionados" in datos_evidencia[user_id] and datos_evidencia[user_id]["gastos_seleccionados"]:
        mensaje_confirmacion = f"Tipo de operación: {tipo_operacion}\n"
        mensaje_confirmacion += "IDs de gastos seleccionados:\n"
        
        for gasto_id in datos_evidencia[user_id]["gastos_seleccionados"]:
            mensaje_confirmacion += f"- {gasto_id}\n"
        
        mensaje_confirmacion += f"Monto total: S/ {monto}\n"
        mensaje_confirmacion += f"Archivo guardado como: {nombre_archivo}"
    else:
        mensaje_confirmacion = f"Tipo de operación: {tipo_operacion}\n"
        mensaje_confirmacion += f"ID de operación: {op_id}\n"
        mensaje_confirmacion += f"Monto: S/ {monto}\n"
        mensaje_confirmacion += f"Archivo guardado como: {nombre_archivo}"
    
    # Añadir información de la carpeta
    mensaje_confirmacion += f"\nCarpeta: {folder_name}"
    
    # Añadir enlace de Drive si está disponible
    if DRIVE_ENABLED and drive_file_info and drive_file_info.get("webViewLink"):
        mensaje_confirmacion += f"\n\nEnlace en Drive: {drive_file_info.get('webViewLink')}"
    
    # Teclado para confirmación
    keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Mostrar la imagen y solicitar confirmación
    await update.message.reply_photo(
        photo=file_id,
        caption=f"📝 RESUMEN\n\n{mensaje_confirmacion}\n\n¿Confirmar la carga de este documento?",
        reply_markup=reply_markup
    )
    
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el documento"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    
    if respuesta not in ["✅ confirmar", "confirmar", "sí", "si", "s", "yes", "y"]:
        # Si no confirma, cancelar y borrar el archivo (solo si es local)
        ruta_archivo = datos_evidencia[user_id].get("ruta_archivo", "")
        if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
            try:
                os.remove(ruta_archivo)
                logger.info(f"Archivo local eliminado tras cancelación: {ruta_archivo}")
            except Exception as e:
                logger.error(f"Error al eliminar archivo local tras cancelación: {e}")
        
        await update.message.reply_text(
            "❌ Operación cancelada.\n\n"
            "El documento no ha sido registrado.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales
        if user_id in datos_evidencia:
            del datos_evidencia[user_id]
        
        return ConversationHandler.END
    
    # Preparar datos para guardar
    documento = datos_evidencia[user_id].copy()
    
    # Generar un ID único para este documento
    documento["id"] = generate_unique_id()
    
    # Añadir fecha actualizada
    now = get_now_peru()
    fecha_formateada = now.strftime("%Y-%m-%d %H:%M")
    documento["fecha"] = format_date_for_sheets(fecha_formateada)
    
    # Añadir notas vacías (para mantener estructura)
    documento["notas"] = ""
    
    # Asegurar que los campos de Drive estén presentes
    if "drive_file_id" not in documento:
        documento["drive_file_id"] = ""
    if "drive_view_link" not in documento:
        documento["drive_view_link"] = ""
    
    # Si es un documento para múltiples gastos, guardar la lista de IDs de gastos
    if documento["tipo_operacion"] == "GASTO" and "gastos_seleccionados" in documento:
        documento["gastos_ids"] = ",".join(documento["gastos_seleccionados"])
    else:
        documento["gastos_ids"] = ""
    
    logger.info(f"Guardando documento en Google Sheets: {documento}")
    
    try:
        # Crear objeto de datos limpio con los campos correctos
        datos_limpios = {
            "id": documento.get("id", ""),
            "fecha": documento.get("fecha", ""),
            "tipo_operacion": documento.get("tipo_operacion", ""),
            "operacion_id": documento.get("operacion_id", ""),
            "archivo_id": documento.get("archivo_id", ""),
            "ruta_archivo": documento.get("ruta_archivo", ""),
            "drive_file_id": documento.get("drive_file_id", ""),
            "drive_view_link": documento.get("drive_view_link", ""),
            "registrado_por": documento.get("registrado_por", ""),
            "gastos_ids": documento.get("gastos_ids", ""),
            "notas": documento.get("notas", "")
        }
        
        # Guardar en Google Sheets
        result = append_sheets("documentos", datos_limpios)
        
        if result:
            logger.info(f"Documento guardado exitosamente para usuario {user_id}")
            
            # Preparar mensaje de éxito
            mensaje = "✅ ¡Documento registrado exitosamente!\n\n"
            mensaje += f"ID del documento: {documento['id']}\n"
            
            # Adaptar mensaje según tipo de operación
            if documento["tipo_operacion"] == "GASTO" and "gastos_seleccionados" in documento and documento["gastos_seleccionados"]:
                mensaje += f"Tipo: {documento['tipo_operacion']}\n"
                mensaje += f"Asociado a {len(documento['gastos_seleccionados'])} gastos\n"
                mensaje += f"Monto total: S/ {documento.get('monto', '0')}\n"
            else:
                mensaje += f"Asociado a: {documento['tipo_operacion']} - {documento['operacion_id']}\n"
                mensaje += f"Monto: S/ {documento.get('monto', '0')}\n"
            
            mensaje += f"Guardado en carpeta: {documento['folder_name']}"
            
            # Añadir enlace de Drive si está disponible
            if DRIVE_ENABLED and documento.get("drive_view_link"):
                mensaje += f"\n\nPuedes ver el documento en Drive:\n{documento['drive_view_link']}"
            
            mensaje += "\n\nUsa /evidencia para registrar otra evidencia."
            
            await update.message.reply_text(
                mensaje,
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            logger.error("Error al guardar documento: La función append_sheets devolvió False")
            await update.message.reply_text(
                "❌ Error al guardar el documento en la base de datos. El archivo fue guardado pero no registrado.\n\n"
                "Contacta al administrador si el problema persiste.",
                reply_markup=ReplyKeyboardRemove()
            )
    except Exception as e:
        logger.error(f"Error al guardar documento: {e}")
        await update.message.reply_text(
            "❌ Error al guardar el documento. Por favor, intenta nuevamente.\n\n"
            f"Error: {str(e)}\n\n"
            "Contacta al administrador si el problema persiste.",
            reply_markup=ReplyKeyboardRemove()
        )
    
    # Limpiar datos temporales
    if user_id in datos_evidencia:
        del datos_evidencia[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló el proceso de carga de evidencia con /cancelar")
    
    # Limpiar datos temporales y eliminar archivo si existe
    if user_id in datos_evidencia:
        # Si se había guardado un archivo local, eliminarlo
        ruta_archivo = datos_evidencia[user_id].get("ruta_archivo", "")
        if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
            try:
                os.remove(ruta_archivo)
                logger.info(f"Archivo eliminado tras cancelación: {ruta_archivo}")
            except Exception as e:
                logger.error(f"Error al eliminar archivo tras cancelación: {e}")
        
        del datos_evidencia[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /evidencia para iniciar de nuevo cuando quieras.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def register_evidencias_handlers(application):
    """Registra los handlers para el módulo de evidencias"""
    try:
        # Crear un handler de conversación para el flujo completo de evidencias
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("evidencia", evidencia_command)],
            states={
                SELECCIONAR_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_tipo)],
                SELECCIONAR_OPERACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_operacion)],
                SELECCIONAR_GASTOS: [CallbackQueryHandler(handle_gasto_selection)],
                SUBIR_DOCUMENTO: [MessageHandler(filters.PHOTO, subir_documento)],
                CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
            },
            fallbacks=[CommandHandler("cancelar", cancelar)],
        )
        
        # Agregar el manejador al dispatcher
        application.add_handler(conv_handler)
        logger.info("Handler de evidencias registrado")
        return True
    except Exception as e:
        logger.error(f"Error al registrar handler de evidencias: {e}")
        logger.error(traceback.format_exc())
        return False