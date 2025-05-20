import logging
import os
import uuid
import traceback
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from utils.sheets import append_data as append_sheets, generate_unique_id, get_all_data
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive, get_file_link
from config import UPLOADS_FOLDER, DRIVE_ENABLED, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID

# Configurar logging
logger = logging.getLogger(__name__)

# Estados para la conversación - CORREGIDO: Mantener estados consecutivos para evitar confusiones
SELECCIONAR_TIPO, SELECCIONAR_REGISTRO, SUBIR_DOCUMENTO, CONFIRMAR = range(4)

# Datos temporales
datos_documento = {}

# Headers para la hoja de documentos
DOCUMENTS_HEADERS = ["id", "fecha", "tipo_operacion", "operacion_id", "archivo_id", "ruta_archivo", "drive_file_id", "drive_view_link", "registrado_por", "notas"]

# Tipos de operaciones soportadas
TIPOS_OPERACION = ["COMPRA", "VENTA"]

# Mapeo de tipos de operación a nombre de hoja
TIPO_HOJA_MAPPING = {
    "COMPRA": "compras",
    "VENTA": "ventas"
}

# Asegurar que existe el directorio de uploads
try:
    if not os.path.exists(UPLOADS_FOLDER):
        os.makedirs(UPLOADS_FOLDER)
        logger.info(f"Directorio de uploads creado: {UPLOADS_FOLDER}")
    else:
        logger.info(f"Directorio de uploads ya existe: {UPLOADS_FOLDER}")
except Exception as e:
    logger.error(f"Error al crear directorio de uploads: {e}")
    logger.error(traceback.format_exc())

async def documento_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de carga de un documento (evidencia de pago)"""
    try:
        user_id = update.effective_user.id
        username = update.effective_user.username or update.effective_user.first_name
        logger.info(f"=== COMANDO /documento INICIADO por {username} (ID: {user_id}) ===")
        
        # Inicializar datos para este usuario
        datos_documento[user_id] = {
            "registrado_por": username
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
    
    except Exception as e:
        logger.error(f"ERROR en documento_command: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al iniciar el comando /documento.\n"
            "Por favor, intenta nuevamente más tarde."
        )
        
        return ConversationHandler.END

async def seleccionar_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el tipo de operación y lista los registros disponibles"""
    user_id = update.effective_user.id
    
    try:
        respuesta = update.message.text.strip().upper()
        logger.info(f"Usuario {user_id} respondió con: '{respuesta}'")
        
        if respuesta.lower() == "❌ cancelar":
            logger.info(f"Usuario {user_id} canceló en selección de tipo")
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
        
        # Obtener el nombre correcto de la hoja según el tipo seleccionado
        nombre_hoja = TIPO_HOJA_MAPPING.get(respuesta, "")
        if not nombre_hoja:
            logger.error(f"ERROR: Nombre de hoja no encontrado para tipo {respuesta}")
            await update.message.reply_text(
                f"⚠️ Error interno: Tipo de operación no reconocido: {respuesta}.\n\n"
                "Por favor, contacta al administrador.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        # Obtener los registros del tipo seleccionado
        registros = None
        try:
            logger.info(f"Obteniendo registros de la hoja '{nombre_hoja}'")
            registros = get_all_data(nombre_hoja)
            logger.info(f"Obtenidos {len(registros)} registros de {nombre_hoja}")
        except Exception as e:
            logger.error(f"Error al obtener registros de {nombre_hoja}: {e}")
            logger.error(traceback.format_exc())
            registros = []
        
        if not registros:
            await update.message.reply_text(
                f"⚠️ No hay registros de {respuesta} disponibles.\n\n"
                "Por favor, verifica que existan registros o selecciona otro tipo de operación.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        # Limitar la lista a los 10 registros más recientes y ordenar por fecha (si está disponible)
        registros_recientes = sorted(
            registros, 
            key=lambda x: x.get('fecha', ''), 
            reverse=True
        )[:10]
        
        # Guardar los registros en el contexto del usuario
        datos_documento[user_id]["registros"] = registros_recientes
        
        # Crear teclado con los registros disponibles
        keyboard = []
        for registro in registros_recientes:
            # Intentar obtener información relevante del registro
            registro_id = registro.get('id', 'Sin ID')
            fecha = registro.get('fecha', 'Sin fecha')
            info_adicional = ''
            
            if respuesta.upper() == 'COMPRA':
                cliente = registro.get('cliente', registro.get('proveedor', 'Sin nombre'))
                cantidad = registro.get('cantidad', 'Sin cantidad')
                info_adicional = f"{cliente} - {cantidad} kg"
            elif respuesta.upper() == 'VENTA':
                cliente = registro.get('cliente', 'Sin cliente')
                cantidad = registro.get('cantidad', 'Sin cantidad')
                info_adicional = f"{cliente} - {cantidad} kg"
            
            # Formato: ID (fecha): Info adicional
            button_text = f"{registro_id} ({fecha}): {info_adicional}"
            if len(button_text) > 40:  # Limitar el tamaño del texto
                button_text = button_text[:37] + "..."
            
            keyboard.append([button_text])
        
        keyboard.append(["❌ Cancelar"])
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            f"📋 REGISTROS DE {respuesta}\n\n"
            f"Selecciona el registro al que deseas adjuntar evidencia de pago:",
            reply_markup=reply_markup
        )
        
        logger.info(f"Mostrando lista de registros a usuario {user_id} (estado: {SELECCIONAR_REGISTRO})")
        return SELECCIONAR_REGISTRO
    
    except Exception as e:
        logger.error(f"ERROR en seleccionar_tipo: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar tu selección.\n"
            "Por favor, intenta nuevamente.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

async def seleccionar_registro(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el registro seleccionado y solicita el documento"""
    user_id = update.effective_user.id
    
    try:
        respuesta = update.message.text.strip()
        logger.info(f"Usuario {user_id} seleccionó registro: '{respuesta}'")
        
        if respuesta.lower() == "❌ cancelar":
            logger.info(f"Usuario {user_id} canceló en selección de registro")
            await cancelar(update, context)
            return ConversationHandler.END
        
        # Extraer el ID del registro seleccionado (asumiendo que está al principio del texto)
        seleccion_id = respuesta.split(' ')[0].strip()
        logger.info(f"ID de registro extraído: {seleccion_id}")
        
        # Buscar el registro correspondiente
        registro_seleccionado = None
        for registro in datos_documento[user_id]["registros"]:
            if registro.get('id', '') == seleccion_id:
                registro_seleccionado = registro
                break
        
        if not registro_seleccionado:
            logger.error(f"No se encontró el registro con ID {seleccion_id}")
            await update.message.reply_text(
                f"⚠️ No se encontró el registro con ID {seleccion_id}.\n"
                "Por favor, intenta nuevamente.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        # Guardar el ID de la operación
        datos_documento[user_id]["operacion_id"] = seleccion_id
        
        # Modo de almacenamiento
        almacenamiento = "Google Drive" if DRIVE_ENABLED else "almacenamiento local"
        logger.info(f"Modo de almacenamiento: {almacenamiento}")
        
        # Detalles del registro seleccionado para mostrar al usuario
        tipo_op = datos_documento[user_id]["tipo_operacion"]
        detalles = ""
        
        if tipo_op == "COMPRA":
            proveedor = registro_seleccionado.get('cliente', registro_seleccionado.get('proveedor', 'Sin nombre'))
            cantidad = registro_seleccionado.get('cantidad', 'No especificada')
            precio = registro_seleccionado.get('precio', 'No especificado')
            total = registro_seleccionado.get('preciototal', 'No especificado')
            fecha = registro_seleccionado.get('fecha', 'No especificada')
            
            detalles = f"Proveedor: {proveedor}\n" \
                      f"Cantidad: {cantidad} kg\n" \
                      f"Precio: S/ {precio} por kg\n" \
                      f"Total: S/ {total}\n" \
                      f"Fecha: {fecha}"
        elif tipo_op == "VENTA":
            cliente = registro_seleccionado.get('cliente', 'Sin cliente')
            cantidad = registro_seleccionado.get('cantidad', 'No especificada')
            precio = registro_seleccionado.get('precio', 'No especificado')
            total = registro_seleccionado.get('total', 'No especificado')
            fecha = registro_seleccionado.get('fecha', 'No especificada')
            
            detalles = f"Cliente: {cliente}\n" \
                      f"Cantidad: {cantidad} kg\n" \
                      f"Precio: S/ {precio} por kg\n" \
                      f"Total: S/ {total}\n" \
                      f"Fecha: {fecha}"
        
        await update.message.reply_text(
            f"📄 DETALLES DEL REGISTRO\n\n"
            f"ID: {seleccion_id}\n"
            f"Tipo: {tipo_op}\n"
            f"{detalles}\n\n"
            f"Por favor, envía la imagen de la evidencia de pago.\n"
            f"La imagen debe ser clara y legible.\n\n"
            f"Nota: La imagen se guardará en {almacenamiento}."
        )
        
        logger.info(f"Solicitando imagen de evidencia a usuario {user_id} (estado: {SUBIR_DOCUMENTO})")
        return SUBIR_DOCUMENTO
    
    except Exception as e:
        logger.error(f"ERROR en seleccionar_registro: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar tu selección.\n"
            "Por favor, intenta nuevamente.",
            reply_markup=ReplyKeyboardRemove()
        )
        
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
        file = await context.bot.get_file(file_id)
        logger.info(f"Obtenido archivo con path: {file.file_path}")
        
        # Crear un nombre único para el archivo
        tipo_op = datos_documento[user_id]["tipo_operacion"].lower()
        op_id = datos_documento[user_id]["operacion_id"]
        nombre_archivo = f"{tipo_op}_{op_id}_{uuid.uuid4().hex[:8]}.jpg"
        logger.info(f"Nombre de archivo generado: {nombre_archivo}")
        
        # Determinar si usar Google Drive o almacenamiento local
        drive_file_info = None
        if DRIVE_ENABLED:
            logger.info("Google Drive está habilitado, intentando subir archivo...")
            try:
                # Descargar el archivo a memoria
                logger.info("Descargando archivo a memoria...")
                file_bytes = await file.download_as_bytearray()
                logger.info(f"Archivo descargado exitosamente, tamaño: {len(file_bytes)} bytes")
                
                # Determinar la carpeta donde guardar el archivo según tipo de operación
                if tipo_op.upper() == "COMPRA":
                    folder_id = DRIVE_EVIDENCIAS_COMPRAS_ID
                    logger.info(f"Guardando evidencia de COMPRA en carpeta ID: {folder_id}")
                else:  # VENTA
                    folder_id = DRIVE_EVIDENCIAS_VENTAS_ID
                    logger.info(f"Guardando evidencia de VENTA en carpeta ID: {folder_id}")
                
                # Subir el archivo a Drive
                logger.info(f"Subiendo archivo a Drive: {nombre_archivo}")
                drive_file_info = upload_file_to_drive(file_bytes, nombre_archivo, "image/jpeg", folder_id)
                
                if drive_file_info:
                    # Guardar la información de Drive
                    datos_documento[user_id]["drive_file_id"] = drive_file_info.get("id")
                    datos_documento[user_id]["drive_view_link"] = drive_file_info.get("webViewLink")
                    logger.info(f"Archivo subido exitosamente a Drive: {drive_file_info}")
                    ruta_completa = f"GoogleDrive:{drive_file_info.get('id')}:{nombre_archivo}"
                else:
                    logger.error("Error al subir archivo a Drive, usando almacenamiento local como respaldo")
                    # Fallback a almacenamiento local
                    ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
                    logger.info(f"Guardando archivo localmente (fallback): {ruta_completa}")
                    await file.download_to_drive(ruta_completa)
            except Exception as e:
                logger.error(f"Error al subir a Drive: {e}")
                logger.error(traceback.format_exc())
                # Fallback a almacenamiento local
                ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
                logger.info(f"Guardando archivo localmente (tras error): {ruta_completa}")
                await file.download_to_drive(ruta_completa)
        else:
            # Almacenamiento local
            ruta_completa = os.path.join(UPLOADS_FOLDER, nombre_archivo)
            logger.info(f"Google Drive deshabilitado. Guardando archivo localmente: {ruta_completa}")
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
        
        logger.info(f"Solicitando confirmación a usuario {user_id} (estado: {CONFIRMAR})")
        return CONFIRMAR
    
    except Exception as e:
        logger.error(f"ERROR en subir_documento: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al procesar la imagen.\n"
            "Por favor, intenta nuevamente.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirma y registra el documento"""
    user_id = update.effective_user.id
    
    try:
        respuesta = update.message.text.lower()
        logger.info(f"Usuario {user_id} respondió a confirmación: '{respuesta}'")
        
        if respuesta not in ["✅ confirmar", "confirmar", "sí", "si", "s", "yes", "y"]:
            logger.info(f"Usuario {user_id} canceló en la confirmación")
            
            # Si no confirma, cancelar y borrar el archivo (solo si es local)
            ruta_archivo = datos_documento[user_id].get("ruta_archivo", "")
            if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
                try:
                    logger.info(f"Eliminando archivo local: {ruta_archivo}")
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
        logger.info(f"ID generado para el documento: {documento['id']}")
        
        # Añadir fecha actualizada
        now = get_now_peru()
        fecha_formateada = now.strftime("%Y-%m-%d %H:%M")
        documento["fecha"] = format_date_for_sheets(fecha_formateada)
        logger.info(f"Fecha del documento: {documento['fecha']}")
        
        # Añadir notas vacías (para mantener estructura)
        documento["notas"] = ""
        
        # Procesar la ruta del archivo
        if "GoogleDrive:" in documento["ruta_archivo"]:
            logger.info("Archivo almacenado en Google Drive")
            # Es un archivo en Drive, mantener la cadena completa para referencia
        else:
            logger.info("Archivo almacenado localmente")
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
            logger.info("Guardando documento en la hoja 'documentos'...")
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
                
                mensaje += "\n\nUsa /documento o /evidencia para registrar otro documento."
                
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
        
        logger.info(f"=== PROCESO COMPLETADO para usuario {user_id} ===")
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"ERROR en confirmar: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "⚠️ Ha ocurrido un error al guardar el documento.\n"
            "Por favor, intenta nuevamente.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela la conversación"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} ejecutó el comando /cancelar")
    
    try:
        # Limpiar datos temporales y eliminar archivo si existe
        if user_id in datos_documento:
            # Si se había guardado un archivo local, eliminarlo
            ruta_archivo = datos_documento[user_id].get("ruta_archivo", "")
            if ruta_archivo and not ruta_archivo.startswith("GoogleDrive:") and os.path.exists(ruta_archivo):
                try:
                    logger.info(f"Eliminando archivo local: {ruta_archivo}")
                    os.remove(ruta_archivo)
                    logger.info(f"Archivo local eliminado tras cancelación: {ruta_archivo}")
                except Exception as e:
                    logger.error(f"Error al eliminar archivo local tras cancelación: {e}")
                    logger.error(traceback.format_exc())
            
            del datos_documento[user_id]
            logger.info(f"Datos temporales eliminados para usuario {user_id}")
        
        await update.message.reply_text(
            "❌ Operación cancelada.\n\n"
            "Usa /documento o /evidencia para iniciar de nuevo cuando quieras.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"ERROR en cancelar: {e}")
        logger.error(traceback.format_exc())
        
        # Notificar al usuario
        await update.message.reply_text(
            "❌ Error al cancelar la operación.\n"
            "El proceso ha sido interrumpido de todos modos.",
            reply_markup=ReplyKeyboardRemove()
        )
        
        return ConversationHandler.END

def register_documents_handlers(application):
    """Registra los handlers para el módulo de documentos"""
    try:
        logger.info("=== REGISTRANDO HANDLERS DE DOCUMENTOS ===")
        
        # Crear manejador de conversación - CORREGIDO: Asegurar que los estados coincidan con los definidos arriba
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("documento", documento_command)],
            states={
                SELECCIONAR_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_tipo)],
                SELECCIONAR_REGISTRO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_registro)],
                SUBIR_DOCUMENTO: [MessageHandler(filters.PHOTO, subir_documento)],
                CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
            },
            fallbacks=[CommandHandler("cancelar", cancelar)],
        )
        
        # Agregar el manejador al dispatcher
        application.add_handler(conv_handler)
        logger.info("Handler de documentos registrado correctamente")
        return True
    
    except Exception as e:
        logger.error(f"ERROR al registrar handler de documentos: {e}")
        logger.error(traceback.format_exc())
        return False

# Log adicional para seguimiento
logger.info("=== MÓDULO DOCUMENTS.PY CARGADO ===")
logger.info(f"DRIVE_ENABLED: {DRIVE_ENABLED}")
logger.info(f"DRIVE_EVIDENCIAS_COMPRAS_ID: {DRIVE_EVIDENCIAS_COMPRAS_ID or 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_VENTAS_ID: {DRIVE_EVIDENCIAS_VENTAS_ID or 'No configurado'}")