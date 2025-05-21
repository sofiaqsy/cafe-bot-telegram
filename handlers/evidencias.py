"""
Manejador para el comando /evidencia.
Este comando permite seleccionar una operación (compra o venta) y subir una evidencia.
"""

import logging
import os
import uuid
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from utils.sheets import get_all_data, append_data as append_sheets, generate_unique_id, get_filtered_data
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive, setup_drive_folders
from config import UPLOADS_FOLDER, DRIVE_ENABLED, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID, DRIVE_EVIDENCIAS_ROOT_ID

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_TIPO, SELECCIONAR_OPERACION, SUBIR_DOCUMENTO, CONFIRMAR = range(4)

# Datos temporales
datos_evidencia = {}

# Asegurar que existe el directorio de uploads
if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)
    logger.info(f"Directorio de uploads creado: {UPLOADS_FOLDER}")

# Asegurar que existen los directorios para cada tipo de operación
COMPRAS_FOLDER = os.path.join(UPLOADS_FOLDER, "compras")
VENTAS_FOLDER = os.path.join(UPLOADS_FOLDER, "ventas")

if not os.path.exists(COMPRAS_FOLDER):
    os.makedirs(COMPRAS_FOLDER)
    logger.info(f"Directorio para evidencias de compras creado: {COMPRAS_FOLDER}")

if not os.path.exists(VENTAS_FOLDER):
    os.makedirs(VENTAS_FOLDER)
    logger.info(f"Directorio para evidencias de ventas creado: {VENTAS_FOLDER}")

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
        "registrado_por": update.effective_user.username or update.effective_user.first_name
    }
    
    # Ofrecer opciones para compras o ventas
    keyboard = [
        ["🛒 Compras"],
        ["💰 Ventas"],
        ["❌ Cancelar"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    mensaje = "📋 *SELECCIONA EL TIPO DE OPERACIÓN*\n\n"
    mensaje += "Elige si quieres registrar una evidencia de compra o de venta."
    
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
    else:
        await update.message.reply_text(
            "❌ Opción no válida. Por favor, selecciona 'Compras' o 'Ventas'.",
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
            
            # Crear teclado con las operaciones - mostrar todas
            keyboard = []
            for operacion in operaciones_recientes:
                operacion_id = operacion.get('id', 'Sin ID')
                
                if tipo_operacion == "COMPRA":
                    # FORMATO SIMPLIFICADO: solo mostrar proveedor, monto y tipo de café
                    proveedor = operacion.get('proveedor', 'Proveedor desconocido')
                    tipo_cafe = operacion.get('tipo_cafe', 'Tipo desconocido')
                    total = operacion.get('preciototal', '0')
                    # Botón solo con la información visible más importante (sin fecha ni ID)
                    boton_text = f"{proveedor} | S/ {total} | {tipo_cafe} | ID:{operacion_id}"
                else:  # VENTA
                    # Para ventas, también simplificar
                    cliente = operacion.get('cliente', 'Cliente desconocido')
                    producto = operacion.get('producto', 'Producto desconocido')
                    # Botón simplificado
                    boton_text = f"{cliente} | {producto} | ID:{operacion_id}"
                
                keyboard.append([boton_text])
            
            keyboard.append(["❌ Cancelar"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            mensaje = f"📋 *SELECCIONA UNA {tipo_operacion} PARA ADJUNTAR EVIDENCIA*\n\n"
            mensaje += f"Mostrando {len(operaciones_recientes)} {operacion_plural} disponibles"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
            
            # Redirigir al estado de selección de operación
            return SELECCIONAR_OPERACION
        else:
            comando_registro = "/compra" if tipo_operacion == "COMPRA" else "/venta"
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
    operacion_sheet = "compras" if tipo_operacion == "COMPRA" else "ventas"
    operacion_data = get_filtered_data(operacion_sheet, {"id": operacion_id})
    
    if operacion_data and len(operacion_data) > 0:
        # Guardar el monto para usarlo en el nombre del archivo
        if tipo_operacion == "COMPRA":
            monto = operacion_data[0].get('preciototal', '0')
        else:  # VENTA
            monto = operacion_data[0].get('total', '0')
        
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
    
    # Crear un nombre único para el archivo incluyendo el monto
    tipo_op = datos_evidencia[user_id]["tipo_operacion"].lower()
    op_id = datos_evidencia[user_id]["operacion_id"]
    monto = datos_evidencia[user_id]["monto"]
    nombre_archivo = f"{tipo_op}_{op_id}_S{monto}_{uuid.uuid4().hex[:8]}.jpg"
    
    # Guardar el nombre del archivo
    datos_evidencia[user_id]["nombre_archivo"] = nombre_archivo
    
    # Determinar la carpeta local según el tipo de operación
    if tipo_op.upper() == "COMPRA":
        local_folder = COMPRAS_FOLDER
        folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID if DRIVE_ENABLED else None
        logger.info(f"Evidencia de COMPRA - Se guardará en la carpeta: {COMPRAS_FOLDER}")
    else:  # VENTA
        local_folder = VENTAS_FOLDER
        folder_id = DRIVE_EVIDENCIAS_VENTAS_ID if DRIVE_ENABLED else None
        logger.info(f"Evidencia de VENTA - Se guardará en la carpeta: {VENTAS_FOLDER}")
    
    # Siempre guardar una copia local primero
    local_path = os.path.join(local_folder, nombre_archivo)
    await file.download_to_drive(local_path)
    logger.info(f"Archivo guardado localmente en: {local_path}")
    datos_evidencia[user_id]["ruta_archivo"] = os.path.join(datos_evidencia[user_id]["folder_name"], nombre_archivo)
    
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
    mensaje_confirmacion = f"Tipo de operación: {datos_evidencia[user_id]['tipo_operacion']}\n" \
                         f"ID de operación: {op_id}\n" \
                         f"Monto: S/ {monto}\n" \
                         f"Archivo guardado como: {nombre_archivo}"
    
    # Añadir información de la carpeta
    folder_name = datos_evidencia[user_id]["folder_name"]
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
            "notas": documento.get("notas", "")
        }
        
        # Guardar en Google Sheets
        result = append_sheets("documentos", datos_limpios)
        
        if result:
            logger.info(f"Documento guardado exitosamente para usuario {user_id}")
            
            # Preparar mensaje de éxito
            mensaje = "✅ ¡Documento registrado exitosamente!\n\n" \
                    f"ID del documento: {documento['id']}\n" \
                    f"Asociado a: {documento['tipo_operacion']} - {documento['operacion_id']}\n" \
                    f"Monto: S/ {documento.get('monto', '0')}\n" \
                    f"Guardado en carpeta: {documento['folder_name']}"
            
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