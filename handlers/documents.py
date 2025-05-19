import logging
import os
import uuid
import traceback
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from utils.sheets import append_data as append_sheets, generate_unique_id
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive, get_file_link
from config import UPLOADS_FOLDER, DRIVE_ENABLED, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID

# Configurar logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG  # Cambiado a DEBUG para más detalles
)
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
try:
    if not os.path.exists(UPLOADS_FOLDER):
        os.makedirs(UPLOADS_FOLDER)
        logger.info(f"Directorio de uploads creado: {UPLOADS_FOLDER}")
    else:
        logger.info(f"Directorio de uploads ya existe: {UPLOADS_FOLDER}")
    
    # Verificar permisos de escritura
    test_file_path = os.path.join(UPLOADS_FOLDER, "test_write.tmp")
    with open(test_file_path, 'w') as f:
        f.write("test")
    os.remove(test_file_path)
    logger.info(f"Permisos de escritura verificados en: {UPLOADS_FOLDER}")

except Exception as e:
    logger.error(f"ERROR al crear/verificar directorio de uploads: {e}")
    logger.error(traceback.format_exc())

# Log de configuración inicial
logger.info(f"Módulo documents.py cargado con éxito")
logger.info(f"Almacenamiento en Drive: {'HABILITADO' if DRIVE_ENABLED else 'DESHABILITADO'}")
logger.info(f"Carpeta de compras en Drive: {DRIVE_EVIDENCIAS_COMPRAS_ID if DRIVE_EVIDENCIAS_COMPRAS_ID else 'No configurada'}")
logger.info(f"Carpeta de ventas en Drive: {DRIVE_EVIDENCIAS_VENTAS_ID if DRIVE_EVIDENCIAS_VENTAS_ID else 'No configurada'}")

async def documento_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de carga de un documento (evidencia de pago)"""
    try:
        # Obtener información del usuario
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        
        logger.info(f"==== COMANDO /documento INICIADO por {username} (ID: {user_id}) ====")
        
        # Inicializar datos para este usuario
        datos_documento[user_id] = {
            "registrado_por": username
        }
        
        # Crear teclado con opciones
        keyboard = [[tipo] for tipo in TIPOS_OPERACION]
        keyboard.append(["❌ Cancelar"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        logger.info(f"Mostrando opciones de tipos de operación a usuario {user_id}")
        
        await update.message.reply_text(
            "📎 CARGAR DOCUMENTO DE EVIDENCIA DE PAGO\n\n"
            "Selecciona el tipo de operación al que pertenece el documento:",
            reply_markup=reply_markup
        )
        
        logger.info(f"Esperando selección de tipo para usuario {user_id}")
        return SELECCIONAR_TIPO
    
    except Exception as e:
        logger.error(f"ERROR en documento_command: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al iniciar el comando /documento. Por favor, intenta más tarde.\n\n"
            f"Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def seleccionar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de operación y solicita el ID"""
    user_id = update.effective_user.id
    try:
        respuesta = update.message.text.strip().upper()
        logger.info(f"Usuario {user_id} respondió: '{respuesta}'")
        
        if respuesta.lower() == "❌ cancelar":
            logger.info(f"Usuario {user_id} seleccionó cancelar")
            await cancelar(update, context)
            return ConversationHandler.END
        
        # Verificar que sea un tipo válido
        if respuesta not in TIPOS_OPERACION:
            logger.warning(f"Usuario {user_id} ingresó tipo inválido: '{respuesta}'")
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
        
        logger.info(f"Esperando ID de operación para usuario {user_id}")
        return SELECCIONAR_ID
    
    except Exception as e:
        logger.error(f"ERROR en seleccionar_tipo: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar tu selección. Por favor, intenta nuevamente.\n\n"
            f"Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def seleccionar_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el ID de la operación y solicita el documento"""
    user_id = update.effective_user.id
    try:
        operacion_id = update.message.text.strip()
        
        logger.info(f"Usuario {user_id} ingresó ID de operación: {operacion_id}")
        datos_documento[user_id]["operacion_id"] = operacion_id
        
        # Modo de almacenamiento
        almacenamiento = "Google Drive" if DRIVE_ENABLED else "almacenamiento local"
        logger.info(f"Usando {almacenamiento} para usuario {user_id}")
        
        await update.message.reply_text(
            f"ID de operación: {operacion_id}\n\n"
            f"Ahora, envía la imagen de la evidencia de pago.\n"
            f"La imagen debe ser clara y legible.\n\n"
            f"Nota: La imagen se guardará en {almacenamiento}."
        )
        
        logger.info(f"Esperando imagen para usuario {user_id}")
        return SUBIR_DOCUMENTO
    
    except Exception as e:
        logger.error(f"ERROR en seleccionar_id: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar el ID. Por favor, intenta nuevamente.\n\n"
            f"Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def subir_documento(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa el documento cargado"""
    user_id = update.effective_user.id
    try:
        # Verificar si el mensaje contiene una foto
        if not update.message.photo:
            logger.warning(f"Usuario {user_id} no envió una foto")
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
        logger.debug(f"Obteniendo detalles del archivo {file_id}")
        file = await context.bot.get_file(file_id)
        logger.debug(f"Archivo obtenido: {file.file_path}")
        
        # Crear un nombre único para el archivo
        tipo_op = datos_documento[user_id]["tipo_operacion"].lower()
        op_id = datos_documento[user_id]["operacion_id"]
        nombre_archivo = f"{tipo_op}_{op_id}_{uuid.uuid4().hex[:8]}.jpg"
        logger.info(f"Nombre de archivo generado: {nombre_archivo}")
        
        # Determinar si usar Google Drive o almacenamiento local
        drive_file_info = None
        if DRIVE_ENABLED:
            logger.info(f"Intentando subir a Google Drive para usuario {user_id}")
            try:
                # Descargar el archivo a memoria
                logger.debug("Descargando archivo a memoria")
                file_bytes = await file.download_as_bytearray()
                logger.debug(f"Archivo descargado, tamaño: {len(file_bytes)} bytes")
                
                # Determinar la carpeta donde guardar el archivo
                folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID if tipo_op.upper() == "COMPRA" else DRIVE_EVIDENCIAS_VENTAS_ID
                logger.debug(f"Usando carpeta de Drive con ID: {folder_id}")
                
                # Subir el archivo a Drive
                logger.info(f"Subiendo archivo a Drive: {nombre_archivo}")
                drive_file_info = upload_file_to_drive(file_bytes, nombre_archivo, "image/jpeg", folder_id)
                
                if drive_file_info:
                    # Guardar la información de Drive
                    logger.info(f"Archivo subido exitosamente a Drive. ID: {drive_file_info.get('id')}")
                    datos_documento[user_id]["drive_file_id"] = drive_file_info.get("id")
                    datos_documento[user_id]["drive_view_link"] = drive_file_info.get("webViewLink")
                    ruta_completa = f"GoogleDrive:{drive_file_info.get('id')}:{nombre_archivo}"
                else:
                    logger.error("Error al subir archivo a Drive, usando almacenamiento local como respaldo")
                    # Fallback a almacenamiento local
                    ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
                    logger.info(f"Guardando archivo localmente en: {ruta_completa}")
                    await file.download_to_drive(ruta_completa)
            except Exception as e:
                logger.error(f"Error al subir a Drive: {e}")
                logger.error(traceback.format_exc())
                # Fallback a almacenamiento local
                ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
                logger.info(f"Guardando archivo localmente en: {ruta_completa} (tras error en Drive)")
                await file.download_to_drive(ruta_completa)
        else:
            # Almacenamiento local
            ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
            logger.info(f"Guardando archivo localmente en: {ruta_completa} (Drive deshabilitado)")
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
            logger.info(f"Enlace de Drive añadido al mensaje para usuario {user_id}")
        
        # Teclado para confirmación
        keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        logger.info(f"Solicitando confirmación a usuario {user_id}")
        
        # Mostrar la imagen y solicitar confirmación
        await update.message.reply_photo(
            photo=file_id,
            caption=f"📝 *RESUMEN*\n\n{mensaje_confirmacion}\n\n"
                    f"¿Confirmar la carga de este documento?",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        logger.info(f"Esperando confirmación para usuario {user_id}")
        return CONFIRMAR
    
    except Exception as e:
        logger.error(f"ERROR en subir_documento: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar la imagen. Por favor, intenta nuevamente.\n\n"
            f"Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el documento"""
    user_id = update.effective_user.id
    try:
        respuesta = update.message.text.lower()
        logger.info(f"Usuario {user_id} respondió a confirmación: '{respuesta}'")
        
        if respuesta not in ["✅ confirmar", "confirmar", "sí", "si", "s", "yes", "y"]:
            logger.info(f"Usuario {user_id} canceló la operación en fase de confirmación")
            
            # Si no confirma, cancelar y borrar el archivo (solo si es local)
            ruta_archivo = datos_documento[user_id].get("ruta_archivo", "")
            if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
                try:
                    os.remove(ruta_archivo)
                    logger.info(f"Archivo local eliminado tras cancelación: {ruta_archivo}")
                except Exception as e:
                    logger.error(f"Error al eliminar archivo local tras cancelación: {e}")
                    logger.error(traceback.format_exc())
            
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
        logger.info(f"ID único generado para documento: {documento['id']}")
        
        # Añadir fecha actualizada
        now = get_now_peru()
        fecha_formateada = now.strftime("%Y-%m-%d %H:%M")
        documento["fecha"] = format_date_for_sheets(fecha_formateada)
        
        # Añadir notas vacías (para mantener estructura)
        documento["notas"] = ""
        
        # Procesar la ruta del archivo
        if "GoogleDrive:" in documento["ruta_archivo"]:
            # Es un archivo en Drive, mantener la cadena completa para referencia
            logger.debug(f"Ruta de archivo en Drive: {documento['ruta_archivo']}")
        else:
            # Es un archivo local, extraer solo el nombre
            documento["ruta_archivo"] = os.path.basename(documento["ruta_archivo"])
            logger.debug(f"Nombre de archivo local: {documento['ruta_archivo']}")
        
        # Asegurar que los campos de Drive estén presentes
        if "drive_file_id" not in documento:
            documento["drive_file_id"] = ""
        if "drive_view_link" not in documento:
            documento["drive_view_link"] = ""
        
        logger.info(f"Preparando registro en Google Sheets para documento ID: {documento['id']}")
        
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
            
            logger.debug(f"Datos a guardar en Sheets: {datos_limpios}")
            
            # Guardar en Google Sheets
            logger.info("Ejecutando append_sheets para guardar documento...")
            result = append_sheets("documentos", datos_limpios)
            
            if result:
                logger.info(f"Documento guardado exitosamente en Sheets para usuario {user_id}")
                
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
            logger.error(f"Error al guardar documento en Sheets: {e}")
            logger.error(traceback.format_exc())
            await update.message.reply_text(
                "❌ Error al guardar el documento. Por favor, intenta nuevamente.\n\n"
                f"Error: {str(e)}\n\n"
                "Contacta al administrador si el problema persiste.",
                reply_markup=ReplyKeyboardRemove()
            )
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            del datos_documento[user_id]
        
        logger.info(f"==== PROCESO DE DOCUMENTO COMPLETADO para usuario {user_id} ====")
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"ERROR en confirmar: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar la confirmación. Por favor, intenta nuevamente.\n\n"
            f"Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales
        if user_id in datos_documento:
            del datos_documento[user_id]
            
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    try:
        logger.info(f"Usuario {user_id} canceló el proceso con /cancelar")
        
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
                    logger.error(traceback.format_exc())
            
            del datos_documento[user_id]
            logger.info(f"Datos temporales eliminados para usuario {user_id}")
        
        await update.message.reply_text(
            "❌ Operación cancelada.\n\n"
            "Usa /documento para iniciar de nuevo cuando quieras.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"ERROR en cancelar: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al cancelar. El proceso ha sido interrumpido.\n\n"
            f"Error: {str(e)}",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Limpiar datos temporales por si acaso
        if user_id in datos_documento:
            del datos_documento[user_id]
            
        return ConversationHandler.END

def register_documents_handlers(application):
    """Registra los handlers para el módulo de documentos"""
    try:
        logger.info("Registrando handlers para el módulo de documentos...")
        
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
        logger.info("ConversationHandler para documentos registrado exitosamente")
        
        # Registrar handler adicional para comando documento (para depuración)
        application.add_handler(
            CommandHandler("documento_test", 
                lambda update, context: logger.info(f"Comando documento_test recibido de {update.effective_user.id}") or 
                update.message.reply_text("Comando documento_test recibido correctamente")
            )
        )
        logger.info("Handler adicional documento_test registrado para depuración")
        
        return True
    
    except Exception as e:
        logger.error(f"ERROR CRITICO al registrar handlers de documentos: {e}")
        logger.error(traceback.format_exc())
        return False