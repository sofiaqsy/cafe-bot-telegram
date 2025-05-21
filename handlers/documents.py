import logging
import os
import uuid
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from utils.sheets import append_data as append_sheets, generate_unique_id, get_all_data
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive, get_file_link
from config import UPLOADS_FOLDER, DRIVE_ENABLED, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación
SELECCIONAR_TIPO, SELECCIONAR_ID, SUBIR_DOCUMENTO, CONFIRMAR = range(4)

# Datos temporales
datos_documento = {}

# Headers para la hoja de documentos
DOCUMENTS_HEADERS = ["id", "fecha", "tipo_operacion", "operacion_id", "archivo_id", "ruta_archivo", "drive_file_id", "drive_view_link", "registrado_por", "notas"]

# Tipos de operaciones soportadas
TIPOS_OPERACION = ["COMPRA", "VENTA"]

# Asegurar que existe el directorio de uploads
if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)
    logger.info(f"Directorio de uploads creado: {UPLOADS_FOLDER}")

async def documento_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de carga de un documento (evidencia de pago)"""
    user_id = update.effective_user.id
    logger.info(f"=== COMANDO /documento INICIADO por {update.effective_user.first_name or update.effective_user.username} (ID: {user_id}) ===")
    
    # Inicializar datos para este usuario
    datos_documento[user_id] = {
        "registrado_por": update.effective_user.username or update.effective_user.first_name
    }
    
    # Crear teclado con opciones
    keyboard = [[tipo] for tipo in TIPOS_OPERACION]
    keyboard.append(["❌ Cancelar"])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "📎 CARGAR DOCUMENTO DE EVIDENCIA DE PAGO\n\n"
        "Selecciona el tipo de operación al que pertenece el documento:",
        reply_markup=reply_markup
    )
    
    logger.info(f"Usuario {user_id} iniciando selección de tipo (estado: {SELECCIONAR_TIPO})")
    return SELECCIONAR_TIPO

async def seleccionar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de operación y solicita el ID"""
    user_id = update.effective_user.id
    respuesta = update.message.text.strip().upper()
    
    if respuesta.lower() == "❌ cancelar":
        await cancelar(update, context)
        return ConversationHandler.END
    
    # Verificar que sea un tipo válido
    if respuesta not in TIPOS_OPERACION:
        keyboard = [[tipo] for tipo in TIPOS_OPERACION]
        keyboard.append(["❌ Cancelar"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "⚠️ Tipo de operación no válido.\n\n"
            "Por favor, selecciona uno de los tipos disponibles:",
            reply_markup=reply_markup
        )
        return SELECCIONAR_TIPO
    
    # Guardar el tipo de operación
    logger.info(f"Usuario {user_id} seleccionó tipo de operación: {respuesta}")
    datos_documento[user_id]["tipo_operacion"] = respuesta
    
    await update.message.reply_text(
        f"Has seleccionado: {respuesta}\n\n"
        f"Por favor, ingresa el ID de la {respuesta.lower()} a la que deseas adjuntar evidencia de pago."
        f"\n\nPuedes encontrar el ID en la confirmación que recibiste al registrar la {respuesta.lower()}.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return SELECCIONAR_ID

async def seleccionar_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el ID de la operación y solicita el documento"""
    user_id = update.effective_user.id
    operacion_id = update.message.text.strip()
    
    logger.info(f"Usuario {user_id} ingresó ID de operación: {operacion_id}")
    datos_documento[user_id]["operacion_id"] = operacion_id
    
    return await solicitar_documento(update, context)

async def solicitar_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Solicita al usuario que envíe el documento/evidencia"""
    user_id = update.effective_user.id
    
    # Verificar que tengamos los datos necesarios
    if "tipo_operacion" not in datos_documento[user_id] or "operacion_id" not in datos_documento[user_id]:
        logger.error(f"Datos incompletos para usuario {user_id}. Falta tipo_operacion o operacion_id")
        await update.message.reply_text(
            "❌ Error: Faltan datos importantes. Por favor, inicia el proceso nuevamente con /documento.",
            reply_markup=ReplyKeyboardRemove()
        )
        if user_id in datos_documento:
            del datos_documento[user_id]
        return ConversationHandler.END
    
    # Modo de almacenamiento
    almacenamiento = "Google Drive" if DRIVE_ENABLED else "almacenamiento local"
    
    await update.message.reply_text(
        f"ID de operación: {datos_documento[user_id]['operacion_id']}\n\n"
        f"Ahora, envía la imagen de la evidencia de pago.\n"
        f"La imagen debe ser clara y legible.\n\n"
        f"Nota: La imagen se guardará en {almacenamiento}."
    )
    
    return SUBIR_DOCUMENTO

async def registro_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Función para iniciar directamente el proceso de carga de documentos con datos preseleccionados.
    Útil para integraciones con otros comandos como /evidencia.
    """
    user_id = update.effective_user.id
    logger.info(f"Inicio directo de registro de documento para usuario {user_id}")
    
    # Inicializar datos para este usuario
    if user_id not in datos_documento:
        datos_documento[user_id] = {
            "registrado_por": update.effective_user.username or update.effective_user.first_name
        }
    
    # Añadir datos preseleccionados si vienen en context.user_data
    if "tipo_operacion" in context.user_data:
        datos_documento[user_id]["tipo_operacion"] = context.user_data["tipo_operacion"]
        # Limpiar dato de context para evitar problemas futuros
        del context.user_data["tipo_operacion"]
    
    if "operacion_id" in context.user_data:
        datos_documento[user_id]["operacion_id"] = context.user_data["operacion_id"]
        # Limpiar dato de context para evitar problemas futuros
        del context.user_data["operacion_id"]
    
    # Pasar a la solicitud de documentos
    return await solicitar_documento(update, context)

async def subir_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el documento cargado"""
    user_id = update.effective_user.id
    
    # Verificar si el mensaje contiene una foto
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Por favor, envía una imagen de la evidencia de pago.\n"
            "Si deseas cancelar, usa el comando /cancelar."
        )
        return SUBIR_DOCUMENTO
    
    # Obtener la foto de mejor calidad (la última en la lista)
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    logger.info(f"Usuario {user_id} subió imagen con file_id: {file_id}")
    
    # Guardar información de la foto
    datos_documento[user_id]["archivo_id"] = file_id
    
    # Obtener el archivo
    file = await context.bot.get_file(file_id)
    
    # Crear un nombre único para el archivo
    tipo_op = datos_documento[user_id]["tipo_operacion"].lower()
    op_id = datos_documento[user_id]["operacion_id"]
    
    # Obtener datos adicionales como monto y proveedor para compras
    monto = ""
    proveedor = ""
    
    if tipo_op.upper() == "COMPRA":
        try:
            # Buscar los datos de la compra para obtener el monto y proveedor
            compras = get_all_data('compras')
            for compra in compras:
                if compra.get('id') == op_id:
                    monto = compra.get('preciototal', '')
                    proveedor = compra.get('proveedor', '').replace(' ', '_')  # Reemplazar espacios con guiones bajos
                    break
        except Exception as e:
            logger.error(f"Error al obtener datos de compra para ID {op_id}: {e}")
    
    # Generar nombre de archivo con formato mejorado
    if tipo_op.upper() == "COMPRA" and monto and proveedor:
        nombre_archivo = f"{tipo_op}_{op_id}_{proveedor}_{monto}.jpg"
    else:
        # Mantener el formato anterior para otros casos o cuando falten datos
        nombre_archivo = f"{tipo_op}_{op_id}_{uuid.uuid4().hex[:8]}.jpg"
    
    # Determinar si usar Google Drive o almacenamiento local
    drive_file_info = None
    if DRIVE_ENABLED:
        try:
            # Descargar el archivo a memoria
            file_bytes = await file.download_as_bytearray()
            
            # Determinar la carpeta donde guardar el archivo según tipo de operación
            if tipo_op.upper() == "COMPRA":
                folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID
                logger.info(f"Guardando evidencia de COMPRA en carpeta ID: {folder_id}")
            else:  # VENTA
                folder_id = DRIVE_EVIDENCIAS_VENTAS_ID
                logger.info(f"Guardando evidencia de VENTA en carpeta ID: {folder_id}")
            
            # Subir el archivo a Drive
            drive_file_info = upload_file_to_drive(file_bytes, nombre_archivo, "image/jpeg", folder_id)
            
            if drive_file_info:
                # Guardar la información de Drive
                datos_documento[user_id]["drive_file_id"] = drive_file_info.get("id")
                datos_documento[user_id]["drive_view_link"] = drive_file_info.get("webViewLink")
                logger.info(f"Archivo subido a Drive: {drive_file_info}")
                ruta_completa = f"GoogleDrive:{drive_file_info.get('id')}:{nombre_archivo}"
            else:
                logger.error("Error al subir archivo a Drive, usando almacenamiento local como respaldo")
                # Fallback a almacenamiento local
                ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
                await file.download_to_drive(ruta_completa)
        except Exception as e:
            logger.error(f"Error al subir a Drive: {e}, usando almacenamiento local como respaldo")
            # Fallback a almacenamiento local
            ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
            await file.download_to_drive(ruta_completa)
    else:
        # Almacenamiento local
        ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
        await file.download_to_drive(ruta_completa)
    
    logger.info(f"Archivo guardado en: {ruta_completa}")
    datos_documento[user_id]["ruta_archivo"] = ruta_completa
    
    # Preparar mensaje de confirmación
    mensaje_confirmacion = f"Tipo de operación: {datos_documento[user_id]['tipo_operacion']}\n" \
                         f"ID de operación: {op_id}\n" \
                         f"Archivo guardado como: {nombre_archivo}"
    
    # Añadir enlace de Drive si está disponible
    if DRIVE_ENABLED and drive_file_info and "drive_view_link" in datos_documento[user_id]:
        mensaje_confirmacion += f"\n\nEnlace en Drive: {datos_documento[user_id]['drive_view_link']}"
    
    # Teclado para confirmación
    keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Mostrar la imagen y solicitar confirmación
    await update.message.reply_photo(
        photo=file_id,
        caption=f"📝 *RESUMEN*\n\n{mensaje_confirmacion}\n\n"
                f"¿Confirmar la carga de este documento?",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    
    return CONFIRMAR

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el documento"""
    user_id = update.effective_user.id
    respuesta = update.message.text.lower()
    
    if respuesta not in ["✅ confirmar", "confirmar", "sí", "si", "s", "yes", "y"]:
        # Si no confirma, cancelar y borrar el archivo (solo si es local)
        ruta_archivo = datos_documento[user_id].get("ruta_archivo", "")
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
        if user_id in datos_documento:
            del datos_documento[user_id]
        
        return ConversationHandler.END
    
    # Preparar datos para guardar
    documento = datos_documento[user_id].copy()
    
    # Generar un ID único para este documento
    documento["id"] = generate_unique_id()
    
    # Añadir fecha actualizada
    now = get_now_peru()
    fecha_formateada = now.strftime("%Y-%m-%d %H:%M")
    documento["fecha"] = format_date_for_sheets(fecha_formateada)
    
    # Añadir notas vacías (para mantener estructura)
    documento["notas"] = ""
    
    # Procesar la ruta del archivo
    if "GoogleDrive:" in documento["ruta_archivo"]:
        # Es un archivo en Drive, mantener la cadena completa para referencia
        pass
    else:
        # Es un archivo local, extraer solo el nombre
        documento["ruta_archivo"] = os.path.basename(documento["ruta_archivo"])
    
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
                    f"Asociado a: {documento['tipo_operacion']} - {documento['operacion_id']}"
            
            # Añadir enlace de Drive si está disponible
            if DRIVE_ENABLED and documento.get("drive_view_link"):
                mensaje += f"\n\nPuedes ver el documento en Drive:\n{documento['drive_view_link']}"
            
            mensaje += "\n\nUsa /documento para registrar otro documento."
            
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
    if user_id in datos_documento:
        del datos_documento[user_id]
    
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} canceló el proceso de carga de documento con /cancelar")
    
    # Limpiar datos temporales y eliminar archivo si existe
    if user_id in datos_documento:
        # Si se había guardado un archivo local, eliminarlo
        ruta_archivo = datos_documento[user_id].get("ruta_archivo", "")
        if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
            try:
                os.remove(ruta_archivo)
                logger.info(f"Archivo eliminado tras cancelación: {ruta_archivo}")
            except Exception as e:
                logger.error(f"Error al eliminar archivo tras cancelación: {e}")
        
        del datos_documento[user_id]
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /documento para iniciar de nuevo cuando quieras.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def register_documents_handlers(application):
    """Registra los handlers para el módulo de documentos"""
    # Crear manejador de conversación
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("documento", documento_command)],
        states={
            SELECCIONAR_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_tipo)],
            SELECCIONAR_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_id)],
            SUBIR_DOCUMENTO: [MessageHandler(filters.PHOTO, subir_documento)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handlers de documentos registrados")