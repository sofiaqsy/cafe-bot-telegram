import logging
import os
import uuid
import traceback
import sys
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from utils.sheets import append_data as append_sheets, generate_unique_id
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive, get_file_link
from config import UPLOADS_FOLDER, DRIVE_ENABLED, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID

# Configurar logging avanzado
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
logging.basicConfig(
    format=LOG_FORMAT,
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler("documento_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Registrar información del entorno de ejecución
logger.info("=" * 80)
logger.info("INICIANDO MÓDULO DOCUMENTS.PY - VERSIÓN DE DIAGNÓSTICO")
logger.info("Python: %s", sys.version)
logger.info("Telegram-bot version: %s", getattr(sys.modules.get('telegram'), '__version__', 'No encontrado'))
logger.info("=" * 80)

# Estados para la conversación
SELECCIONAR_TIPO, SELECCIONAR_ID, SUBIR_DOCUMENTO, CONFIRMAR = range(4)

# Datos temporales
datos_documento = {}

# Headers para la hoja de documentos
DOCUMENTS_HEADERS = ["id", "fecha", "tipo_operacion", "operacion_id", "archivo_id", "ruta_archivo", "drive_file_id", "drive_view_link", "registrado_por", "notas"]

# Tipos de operaciones soportadas
TIPOS_OPERACION = ["COMPRA", "VENTA"]

# Asegurar que existe el directorio de uploads con manejo de excepciones detallado
try:
    logger.debug("Verificando directorio de uploads: %s", UPLOADS_FOLDER)
    if not os.path.exists(UPLOADS_FOLDER):
        os.makedirs(UPLOADS_FOLDER)
        logger.info("Directorio de uploads creado exitosamente: %s", UPLOADS_FOLDER)
    else:
        logger.info("Directorio de uploads ya existe: %s", UPLOADS_FOLDER)
    
    # Verificar permisos de escritura
    test_file_path = os.path.join(UPLOADS_FOLDER, "test_write.tmp")
    logger.debug("Probando permisos de escritura en: %s", test_file_path)
    with open(test_file_path, 'w') as f:
        f.write("test")
    os.remove(test_file_path)
    logger.info("Permisos de escritura verificados exitosamente en: %s", UPLOADS_FOLDER)

except Exception as e:
    logger.critical("ERROR CRÍTICO al crear/verificar directorio de uploads: %s", e)
    logger.critical("Traceback completo: %s", traceback.format_exc())
    logger.critical("Este error puede impedir el funcionamiento del módulo de documentos")

# Log de configuración inicial
logger.info("Configuración del módulo documents.py:")
logger.info("- Almacenamiento en Drive: %s", 'HABILITADO' if DRIVE_ENABLED else 'DESHABILITADO')
logger.info("- Carpeta de compras en Drive: %s", DRIVE_EVIDENCIAS_COMPRAS_ID if DRIVE_EVIDENCIAS_COMPRAS_ID else 'No configurada')
logger.info("- Carpeta de ventas en Drive: %s", DRIVE_EVIDENCIAS_VENTAS_ID if DRIVE_EVIDENCIAS_VENTAS_ID else 'No configurada')

# Función auxiliar para validar handler
def validate_handler():
    """Valida que todos los componentes necesarios para el handler estén disponibles"""
    valid = True
    
    # Verificar variables de entorno y configuración
    logger.debug("Validando configuración...")
    if not UPLOADS_FOLDER:
        logger.error("Error de validación: UPLOADS_FOLDER no está configurado")
        valid = False
    
    if DRIVE_ENABLED:
        if not DRIVE_EVIDENCIAS_COMPRAS_ID:
            logger.warning("Advertencia de validación: DRIVE_EVIDENCIAS_COMPRAS_ID no está configurado pero Drive está habilitado")
        if not DRIVE_EVIDENCIAS_VENTAS_ID:
            logger.warning("Advertencia de validación: DRIVE_EVIDENCIAS_VENTAS_ID no está configurado pero Drive está habilitado")
    
    # Verificar que las funciones necesarias estén disponibles
    logger.debug("Validando funciones requeridas...")
    required_functions = [
        (append_sheets, "append_sheets"),
        (generate_unique_id, "generate_unique_id"),
        (get_now_peru, "get_now_peru"),
        (format_date_for_sheets, "format_date_for_sheets")
    ]
    
    for func, name in required_functions:
        if func is None:
            logger.error("Error de validación: Función requerida '%s' no está disponible", name)
            valid = False
    
    if DRIVE_ENABLED:
        drive_functions = [
            (upload_file_to_drive, "upload_file_to_drive"),
            (get_file_link, "get_file_link")
        ]
        for func, name in drive_functions:
            if func is None:
                logger.error("Error de validación: Función de Drive '%s' no está disponible pero Drive está habilitado", name)
                valid = False
    
    # Verificar que los estados de conversación sean correctos
    logger.debug("Validando estados de conversación...")
    if not (isinstance(SELECCIONAR_TIPO, int) and isinstance(SELECCIONAR_ID, int) and isinstance(SUBIR_DOCUMENTO, int) and isinstance(CONFIRMAR, int)):
        logger.error("Error de validación: Los estados de conversación deben ser enteros")
        valid = False
    
    if not (SELECCIONAR_TIPO != SELECCIONAR_ID != SUBIR_DOCUMENTO != CONFIRMAR):
        logger.error("Error de validación: Los estados de conversación deben ser distintos entre sí")
        valid = False
    
    logger.info("Validación del handler completada. Resultado: %s", "VÁLIDO" if valid else "INVÁLIDO")
    return valid

async def documento_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de carga de un documento (evidencia de pago)"""
    try:
        # Obtener información del usuario
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        logger.info("==== COMANDO /documento INICIADO por %s (ID: %s) ====", username, user_id)
        
        # Inicializar datos para este usuario
        datos_documento[user_id] = {
            "registrado_por": username
        }
        
        # Crear teclado con opciones
        keyboard = [[tipo] for tipo in TIPOS_OPERACION]
        keyboard.append(["❌ Cancelar"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        logger.debug("Enviando opciones de tipo de operación a usuario %s", user_id)
        
        await update.message.reply_text(
            "📎 CARGAR DOCUMENTO DE EVIDENCIA DE PAGO\n\n"
            "Selecciona el tipo de operación al que pertenece el documento:",
            reply_markup=reply_markup
        )
        
        logger.info("Enviando al estado SELECCIONAR_TIPO (estado: %s)", SELECCIONAR_TIPO)
        return SELECCIONAR_TIPO
    
    except Exception as e:
        logger.critical("ERROR FATAL en documento_command: %s", e)
        logger.critical("Traceback completo: %s", traceback.format_exc())
        logger.critical("Context: %s", str(context))
        logger.critical("Update: %s", str(update))
        
        # Notificar al usuario
        try:
            await update.message.reply_text(
                "⚠️ Ha ocurrido un error al iniciar el comando /documento. Por favor, intenta más tarde.\n\n"
                f"Error de diagnóstico: {type(e).__name__} - {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e2:
            logger.error("Error adicional al notificar al usuario: %s", e2)
        
        return ConversationHandler.END

async def seleccionar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de operación y solicita el ID"""
    user_id = update.effective_user.id
    logger.debug("Ejecutando seleccionar_tipo para usuario %s", user_id)
    
    try:
        respuesta = update.message.text.strip().upper()
        logger.info("Usuario %s respondió: '%s'", user_id, respuesta)
        
        if respuesta.lower() == "❌ cancelar":
            logger.info("Usuario %s seleccionó cancelar", user_id)
            await cancelar(update, context)
            return ConversationHandler.END
        
        # Verificar que sea un tipo válido
        if respuesta not in TIPOS_OPERACION:
            logger.warning("Usuario %s ingresó tipo inválido: '%s'", user_id, respuesta)
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
        logger.info("Usuario %s seleccionó tipo de operación: %s", user_id, respuesta)
        
        if user_id not in datos_documento:
            logger.error("ERROR: datos_documento[%s] no existe. Recreando diccionario...", user_id)
            datos_documento[user_id] = {"registrado_por": update.effective_user.username or update.effective_user.first_name}
        
        datos_documento[user_id]["tipo_operacion"] = respuesta
        
        await update.message.reply_text(
            f"Has seleccionado: {respuesta}\n\n"
            f"Por favor, ingresa el ID de la {respuesta.lower()} a la que deseas adjuntar evidencia de pago."
            f"\n\nPuedes encontrar el ID en la confirmación que recibiste al registrar la {respuesta.lower()}.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        logger.info("Pasando al estado SELECCIONAR_ID (estado: %s)", SELECCIONAR_ID)
        return SELECCIONAR_ID
    
    except Exception as e:
        logger.critical("ERROR FATAL en seleccionar_tipo: %s", e)
        logger.critical("Traceback completo: %s", traceback.format_exc())
        
        # Notificar al usuario
        try:
            await update.message.reply_text(
                "⚠️ Ha ocurrido un error al procesar tu selección. Por favor, intenta nuevamente.\n\n"
                f"Error de diagnóstico: {type(e).__name__} - {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e2:
            logger.error("Error adicional al notificar al usuario: %s", e2)
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def seleccionar_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el ID de la operación y solicita el documento"""
    user_id = update.effective_user.id
    logger.debug("Ejecutando seleccionar_id para usuario %s", user_id)
    
    try:
        operacion_id = update.message.text.strip()
        
        logger.info("Usuario %s ingresó ID de operación: %s", user_id, operacion_id)
        
        if user_id not in datos_documento:
            logger.error("ERROR: datos_documento[%s] no existe. Recreando diccionario...", user_id)
            datos_documento[user_id] = {
                "registrado_por": update.effective_user.username or update.effective_user.first_name,
                "tipo_operacion": "DESCONOCIDO"  # Valor por defecto
            }
        
        datos_documento[user_id]["operacion_id"] = operacion_id
        
        # Modo de almacenamiento
        almacenamiento = "Google Drive" if DRIVE_ENABLED else "almacenamiento local"
        logger.info("Usando %s para usuario %s", almacenamiento, user_id)
        
        await update.message.reply_text(
            f"ID de operación: {operacion_id}\n\n"
            f"Ahora, envía la imagen de la evidencia de pago.\n"
            f"La imagen debe ser clara y legible.\n\n"
            f"Nota: La imagen se guardará en {almacenamiento}."
        )
        
        logger.info("Pasando al estado SUBIR_DOCUMENTO (estado: %s)", SUBIR_DOCUMENTO)
        return SUBIR_DOCUMENTO
    
    except Exception as e:
        logger.critical("ERROR FATAL en seleccionar_id: %s", e)
        logger.critical("Traceback completo: %s", traceback.format_exc())
        
        # Notificar al usuario
        try:
            await update.message.reply_text(
                "⚠️ Ha ocurrido un error al procesar el ID. Por favor, intenta nuevamente.\n\n"
                f"Error de diagnóstico: {type(e).__name__} - {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e2:
            logger.error("Error adicional al notificar al usuario: %s", e2)
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            logger.debug("Eliminando datos temporales para usuario %s", user_id)
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def subir_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el documento cargado"""
    user_id = update.effective_user.id
    logger.debug("Ejecutando subir_documento para usuario %s", user_id)
    
    try:
        # Verificar si el mensaje contiene una foto
        if not update.message.photo:
            logger.warning("Usuario %s no envió una foto", user_id)
            await update.message.reply_text(
                "⚠️ Por favor, envía una imagen de la evidencia de pago.\n"
                "Si deseas cancelar, usa el comando /cancelar."
            )
            return SUBIR_DOCUMENTO
        
        # Obtener la foto de mejor calidad (la última en la lista)
        photo = update.message.photo[-1]
        file_id = photo.file_id
        
        logger.info("Usuario %s subió imagen con file_id: %s", user_id, file_id)
        
        # Verificar si existen los datos para este usuario
        if user_id not in datos_documento:
            logger.error("ERROR: datos_documento[%s] no existe. Recreando diccionario...", user_id)
            datos_documento[user_id] = {
                "registrado_por": update.effective_user.username or update.effective_user.first_name,
                "tipo_operacion": "DESCONOCIDO",  # Valor por defecto
                "operacion_id": "DESCONOCIDO"  # Valor por defecto
            }
        
        # Guardar información de la foto
        datos_documento[user_id]["archivo_id"] = file_id
        
        # Obtener el archivo
        logger.debug("Obteniendo detalles del archivo %s", file_id)
        try:
            file = await context.bot.get_file(file_id)
            logger.debug("Archivo obtenido: %s", file.file_path)
        except Exception as e:
            logger.error("Error al obtener archivo con ID %s: %s", file_id, e)
            await update.message.reply_text(
                "⚠️ Error al obtener la imagen. Por favor, intenta enviando otra imagen."
            )
            return SUBIR_DOCUMENTO
        
        # Crear un nombre único para el archivo
        tipo_op = datos_documento[user_id]["tipo_operacion"].lower()
        op_id = datos_documento[user_id]["operacion_id"]
        nombre_archivo = f"{tipo_op}_{op_id}_{uuid.uuid4().hex[:8]}.jpg"
        logger.info("Nombre de archivo generado: %s", nombre_archivo)
        
        # Determinar si usar Google Drive o almacenamiento local
        drive_file_info = None
        if DRIVE_ENABLED:
            logger.info("Intentando subir a Google Drive para usuario %s", user_id)
            try:
                # Descargar el archivo a memoria
                logger.debug("Descargando archivo a memoria")
                file_bytes = await file.download_as_bytearray()
                logger.debug("Archivo descargado, tamaño: %s bytes", len(file_bytes))
                
                # Determinar la carpeta donde guardar el archivo
                folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID if tipo_op.upper() == "COMPRA" else DRIVE_EVIDENCIAS_VENTAS_ID
                logger.debug("Usando carpeta de Drive con ID: %s", folder_id)
                
                # Subir el archivo a Drive
                logger.info("Subiendo archivo a Drive: %s", nombre_archivo)
                drive_file_info = upload_file_to_drive(file_bytes, nombre_archivo, "image/jpeg", folder_id)
                
                if drive_file_info:
                    # Guardar la información de Drive
                    logger.info("Archivo subido exitosamente a Drive. ID: %s", drive_file_info.get('id'))
                    datos_documento[user_id]["drive_file_id"] = drive_file_info.get("id")
                    datos_documento[user_id]["drive_view_link"] = drive_file_info.get("webViewLink")
                    ruta_completa = f"GoogleDrive:{drive_file_info.get('id')}:{nombre_archivo}"
                else:
                    logger.error("Error al subir archivo a Drive, usando almacenamiento local como respaldo")
                    # Fallback a almacenamiento local
                    ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
                    logger.info("Guardando archivo localmente en: %s", ruta_completa)
                    await file.download_to_drive(ruta_completa)
            except Exception as e:
                logger.error("Error al subir a Drive: %s", e)
                logger.error("Traceback completo: %s", traceback.format_exc())
                # Fallback a almacenamiento local
                ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
                logger.info("Guardando archivo localmente en: %s (tras error en Drive)", ruta_completa)
                await file.download_to_drive(ruta_completa)
        else:
            # Almacenamiento local
            ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
            logger.info("Guardando archivo localmente en: %s (Drive deshabilitado)", ruta_completa)
            await file.download_to_drive(ruta_completa)
        
        logger.info("Archivo guardado en: %s", ruta_completa)
        datos_documento[user_id]["ruta_archivo"] = ruta_completa
        
        # Preparar mensaje de confirmación
        mensaje_confirmacion = f"Tipo de operación: {datos_documento[user_id]['tipo_operacion']}\n" \
                             f"ID de operación: {op_id}\n" \
                             f"Archivo guardado como: {nombre_archivo}"
        
        # Añadir enlace de Drive si está disponible
        if DRIVE_ENABLED and drive_file_info and "drive_view_link" in datos_documento[user_id]:
            mensaje_confirmacion += f"\n\nEnlace en Drive: {datos_documento[user_id]['drive_view_link']}"
            logger.info("Enlace de Drive añadido al mensaje para usuario %s", user_id)
        
        # Teclado para confirmación
        keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        logger.info("Solicitando confirmación a usuario %s", user_id)
        
        # Mostrar la imagen y solicitar confirmación
        await update.message.reply_photo(
            photo=file_id,
            caption=f"📝 *RESUMEN*\n\n{mensaje_confirmacion}\n\n"
                    f"¿Confirmar la carga de este documento?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        logger.info("Pasando al estado CONFIRMAR (estado: %s)", CONFIRMAR)
        return CONFIRMAR
    
    except Exception as e:
        logger.critical("ERROR FATAL en subir_documento: %s", e)
        logger.critical("Traceback completo: %s", traceback.format_exc())
        
        # Notificar al usuario
        try:
            await update.message.reply_text(
                "⚠️ Ha ocurrido un error al procesar la imagen. Por favor, intenta nuevamente.\n\n"
                f"Error de diagnóstico: {type(e).__name__} - {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e2:
            logger.error("Error adicional al notificar al usuario: %s", e2)
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            logger.debug("Eliminando datos temporales para usuario %s", user_id)
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el documento"""
    user_id = update.effective_user.id
    logger.debug("Ejecutando confirmar para usuario %s", user_id)
    
    try:
        respuesta = update.message.text.lower()
        logger.info("Usuario %s respondió a confirmación: '%s'", user_id, respuesta)
        
        if respuesta not in ["✅ confirmar", "confirmar", "sí", "si", "s", "yes", "y"]:
            logger.info("Usuario %s canceló la operación en fase de confirmación", user_id)
            
            # Si no confirma, cancelar y borrar el archivo (solo si es local)
            if user_id in datos_documento:
                ruta_archivo = datos_documento[user_id].get("ruta_archivo", "")
                if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
                    try:
                        os.remove(ruta_archivo)
                        logger.info("Archivo local eliminado tras cancelación: %s", ruta_archivo)
                    except Exception as e:
                        logger.error("Error al eliminar archivo local tras cancelación: %s", e)
                        logger.error("Traceback: %s", traceback.format_exc())
            
            await update.message.reply_text(
                "❌ Operación cancelada.\n\n"
                "El documento no ha sido registrado.",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Limpiar datos temporales
            if user_id in datos_documento:
                logger.debug("Eliminando datos temporales para usuario %s", user_id)
                del datos_documento[user_id]
            
            return ConversationHandler.END
        
        # Verificar si existen los datos para este usuario
        if user_id not in datos_documento:
            logger.error("ERROR CRÍTICO: datos_documento[%s] no existe en fase de confirmación", user_id)
            await update.message.reply_text(
                "⚠️ Error crítico: No se encontraron los datos de tu documento.\n"
                "Por favor, inicia el proceso de nuevo con /documento.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        # Preparar datos para guardar
        documento = datos_documento[user_id].copy()
        
        # Verificar campos obligatorios
        required_fields = ["tipo_operacion", "operacion_id", "archivo_id", "ruta_archivo", "registrado_por"]
        missing_fields = [field for field in required_fields if field not in documento or not documento[field]]
        
        if missing_fields:
            logger.error("ERROR: Faltan campos obligatorios en los datos del documento: %s", missing_fields)
            await update.message.reply_text(
                "⚠️ Error: Faltan datos obligatorios para completar el registro.\n"
                "Por favor, inicia el proceso de nuevo con /documento.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        # Generar un ID único para este documento
        documento["id"] = generate_unique_id()
        logger.info("ID único generado para documento: %s", documento['id'])
        
        # Añadir fecha actualizada
        now = get_now_peru()
        fecha_formateada = now.strftime("%Y-%m-%d %H:%M")
        documento["fecha"] = format_date_for_sheets(fecha_formateada)
        
        # Añadir notas vacías (para mantener estructura)
        documento["notas"] = ""
        
        # Procesar la ruta del archivo
        if "GoogleDrive:" in documento["ruta_archivo"]:
            # Es un archivo en Drive, mantener la cadena completa para referencia
            logger.debug("Ruta de archivo en Drive: %s", documento['ruta_archivo'])
        else:
            # Es un archivo local, extraer solo el nombre
            documento["ruta_archivo"] = os.path.basename(documento["ruta_archivo"])
            logger.debug("Nombre de archivo local: %s", documento['ruta_archivo'])
        
        # Asegurar que los campos de Drive estén presentes
        if "drive_file_id" not in documento:
            documento["drive_file_id"] = ""
        if "drive_view_link" not in documento:
            documento["drive_view_link"] = ""
        
        logger.info("Preparando registro en Google Sheets para documento ID: %s", documento['id'])
        
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
            
            logger.debug("Datos a guardar en Sheets: %s", datos_limpios)
            
            # Guardar en Google Sheets
            logger.info("Ejecutando append_sheets para guardar documento...")
            result = append_sheets("documentos", datos_limpios)
            
            if result:
                logger.info("Documento guardado exitosamente en Sheets para usuario %s", user_id)
                
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
            logger.error("Error al guardar documento en Sheets: %s", e)
            logger.error("Traceback completo: %s", traceback.format_exc())
            await update.message.reply_text(
                "❌ Error al guardar el documento. Por favor, intenta nuevamente.\n\n"
                f"Error de diagnóstico: {type(e).__name__} - {str(e)}\n\n"
                "Contacta al administrador si el problema persiste.",
                reply_markup=ReplyKeyboardRemove()
            )
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            logger.debug("Eliminando datos temporales para usuario %s", user_id)
            del datos_documento[user_id]
        
        logger.info("==== PROCESO DE DOCUMENTO COMPLETADO para usuario %s ====", user_id)
        return ConversationHandler.END
    
    except Exception as e:
        logger.critical("ERROR FATAL en confirmar: %s", e)
        logger.critical("Traceback completo: %s", traceback.format_exc())
        
        # Notificar al usuario
        try:
            await update.message.reply_text(
                "⚠️ Ha ocurrido un error al procesar la confirmación. Por favor, intenta nuevamente.\n\n"
                f"Error de diagnóstico: {type(e).__name__} - {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e2:
            logger.error("Error adicional al notificar al usuario: %s", e2)
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            logger.debug("Eliminando datos temporales para usuario %s", user_id)
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.debug("Ejecutando cancelar para usuario %s", user_id)
    
    try:
        logger.info("Usuario %s canceló el proceso con /cancelar", user_id)
        
        # Limpiar datos temporales y eliminar archivo si existe
        if user_id in datos_documento:
            # Si se había guardado un archivo local, eliminarlo
            ruta_archivo = datos_documento[user_id].get("ruta_archivo", "")
            if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
                try:
                    os.remove(ruta_archivo)
                    logger.info("Archivo eliminado tras cancelación: %s", ruta_archivo)
                except Exception as e:
                    logger.error("Error al eliminar archivo tras cancelación: %s", e)
                    logger.error("Traceback: %s", traceback.format_exc())
            
            del datos_documento[user_id]
            logger.info("Datos temporales eliminados para usuario %s", user_id)
        
        await update.message.reply_text(
            "❌ Operación cancelada.\n\n"
            "Usa /documento para iniciar de nuevo cuando quieras.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.critical("ERROR FATAL en cancelar: %s", e)
        logger.critical("Traceback completo: %s", traceback.format_exc())
        
        # Notificar al usuario
        try:
            await update.message.reply_text(
                "⚠️ Ha ocurrido un error al cancelar. El proceso ha sido interrumpido.\n\n"
                f"Error de diagnóstico: {type(e).__name__} - {str(e)}",
                reply_markup=ReplyKeyboardRemove()
            )
        except Exception as e2:
            logger.error("Error adicional al notificar al usuario: %s", e2)
        
        # Limpiar datos temporales por si acaso
        if user_id in datos_documento:
            logger.debug("Forzando eliminación de datos temporales para usuario %s", user_id)
            del datos_documento[user_id]
            
        return ConversationHandler.END

# Función simple para probar que el módulo funciona
async def test_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Función simple para verificar que el módulo está cargado correctamente"""
    logger.info("Comando test_documento ejecutado por usuario %s", update.effective_user.id)
    await update.message.reply_text(
        "✅ El módulo de documentos está cargado correctamente.\n\n"
        "Usa /documento para registrar un documento."
    )

def register_documents_handlers(application):
    """Registra los handlers para el módulo de documentos"""
    try:
        logger.info("Iniciando registro de handlers para el módulo de documentos...")
        
        # Validar el handler antes de registrarlo
        handler_valid = validate_handler()
        if not handler_valid:
            logger.warning("Validación del handler falló. Se intentará registrar de todos modos, pero puede fallar.")
        
        # Primero, registrar el comando de prueba
        logger.debug("Registrando comando de prueba test_documento...")
        application.add_handler(CommandHandler("test_documento", test_documento))
        logger.info("Comando de prueba test_documento registrado exitosamente")
        
        # Crear manejador de conversación
        logger.debug("Creando ConversationHandler para /documento...")
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
        logger.debug("Agregando ConversationHandler a la aplicación...")
        application.add_handler(conv_handler)
        logger.info("ConversationHandler para documentos registrado exitosamente")
        
        # También registrar el comando /documento como handler directo para diagnóstico
        logger.debug("Registrando CommandHandler directo para /documento (respaldo)...")
        
        # Función de respaldo para /documento
        async def documento_fallback(update, context):
            logger.info("Ejecutando handler de respaldo para /documento")
            await update.message.reply_text(
                "ℹ️ Intentando iniciar proceso de documento usando handler alternativo.\n"
                "Por favor, usa el comando /test_documento para verificar si el módulo está cargado correctamente."
            )
            # Intentar ejecutar la función documento_command directamente
            try:
                return await documento_command(update, context)
            except Exception as e:
                logger.error("Error en handler de respaldo: %s", e)
                await update.message.reply_text(
                    "❌ Error en handler alternativo. Por favor, contacta al administrador."
                )
                return ConversationHandler.END
        
        # Agregar comando de respaldo
        application.add_handler(CommandHandler("documento_fallback", documento_fallback))
        logger.info("Handler alternativo documento_fallback registrado para diagnóstico")
        
        logger.info("Todos los handlers para el módulo de documentos registrados exitosamente")
        return True
    
    except Exception as e:
        logger.critical("ERROR CRÍTICO al registrar handlers de documentos: %s", e)
        logger.critical("Traceback completo: %s", traceback.format_exc())
        
        # Intentar registrar al menos el comando de prueba si todo lo demás falla
        try:
            application.add_handler(CommandHandler("test_documento", test_documento))
            logger.info("Comando de prueba test_documento registrado como último recurso")
        except:
            pass
        
        return False

# Si este archivo se ejecuta directamente, registrar información para diagnóstico
if __name__ == "__main__":
    logger.info("Este módulo no debe ejecutarse directamente. Importarlo desde bot.py")
    logger.info("Información del entorno para diagnóstico:")
    logger.info("- Python: %s", sys.version)
    logger.info("- Sistema operativo: %s", os.name)
    logger.info("- Directorio actual: %s", os.getcwd())
    logger.info("- Directorio de uploads: %s", UPLOADS_FOLDER)
    logger.info("- Drive habilitado: %s", DRIVE_ENABLED)
    
    # Validar el handler
    validate_handler()