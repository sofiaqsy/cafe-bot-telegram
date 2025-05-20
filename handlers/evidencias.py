"""
Manejador para el comando /evidencia.
Este comando permite seleccionar una operación (compra o venta) y subir una evidencia.
"""

import logging
import os
import uuid
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from utils.sheets import get_all_data, append_data as append_sheets, generate_unique_id
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive
from config import UPLOADS_FOLDER, DRIVE_ENABLED, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID

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
    
    # Mostrar las operaciones recientes en un teclado seleccionable
    try:
        # Obtener datos según el tipo de operación seleccionado
        operaciones = get_all_data(operacion_plural)
        
        if operaciones:
            # Ordenar las operaciones por fecha (más recientes primero)
            operaciones_recientes = sorted(operaciones, key=lambda x: x.get('fecha', ''), reverse=True)[:10]
            
            # Crear teclado con las operaciones
            keyboard = []
            for operacion in operaciones_recientes:
                operacion_id = operacion.get('id', 'Sin ID')
                
                if tipo_operacion == "COMPRA":
                    # Para compras, mostrar proveedor y tipo de café
                    proveedor = operacion.get('proveedor', 'Proveedor desconocido')
                    tipo_cafe = operacion.get('tipo_cafe', 'Tipo desconocido')
                    descripcion = f"{proveedor}, {tipo_cafe}"
                else:  # VENTA
                    # Para ventas, mostrar cliente y producto
                    cliente = operacion.get('cliente', 'Cliente desconocido')
                    producto = operacion.get('producto', 'Producto desconocido')
                    descripcion = f"{cliente}, {producto}"
                
                # Formatear fecha sin hora (solo YYYY-MM-DD)
                fecha_completa = operacion.get('fecha', '')
                fecha_corta = fecha_completa.split(' ')[0] if ' ' in fecha_completa else fecha_completa
                
                # Crear botón con el formato: descripción, fecha(sin hora), id
                boton_text = f"{descripcion}, {fecha_corta}, {operacion_id}"
                keyboard.append([boton_text])
            
            keyboard.append(["❌ Cancelar"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            mensaje = f"📋 *SELECCIONA UNA {tipo_operacion} PARA ADJUNTAR EVIDENCIA*\n\n"
            
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
    
    # Extraer el ID de la operación (que está al final de la línea después de la última coma)
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
    
    # Crear un nombre único para el archivo
    tipo_op = datos_evidencia[user_id]["tipo_operacion"].lower()
    op_id = datos_evidencia[user_id]["operacion_id"]
    nombre_archivo = f"{tipo_op}_{op_id}_{uuid.uuid4().hex[:8]}.jpg"
    
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
    
    # Determinar si usar Google Drive o almacenamiento local
    drive_file_info = None
    if DRIVE_ENABLED and folder_id:
        try:
            # Descargar el archivo a memoria
            file_bytes = await file.download_as_bytearray()
            
            # Subir el archivo a Drive
            drive_file_info = upload_file_to_drive(file_bytes, nombre_archivo, "image/jpeg", folder_id)
            
            if drive_file_info:
                # Guardar la información de Drive
                datos_evidencia[user_id]["drive_file_id"] = drive_file_info.get("id")
                datos_evidencia[user_id]["drive_view_link"] = drive_file_info.get("webViewLink")
                logger.info(f"Archivo subido a Drive: {drive_file_info}")
                ruta_completa = f"GoogleDrive:{drive_file_info.get('id')}:{nombre_archivo}"
            else:
                logger.error("Error al subir archivo a Drive, usando almacenamiento local como respaldo")
                # Fallback a almacenamiento local
                ruta_completa = os.path.join(local_folder, nombre_archivo)
                await file.download_to_drive(ruta_completa)
        except Exception as e:
            logger.error(f"Error al subir a Drive: {e}, usando almacenamiento local como respaldo")
            # Fallback a almacenamiento local
            ruta_completa = os.path.join(local_folder, nombre_archivo)
            await file.download_to_drive(ruta_completa)
    else:
        # Almacenamiento local específico para el tipo de operación
        ruta_completa = os.path.join(local_folder, nombre_archivo)
        await file.download_to_drive(ruta_completa)
    
    logger.info(f"Archivo guardado en: {ruta_completa}")
    datos_evidencia[user_id]["ruta_archivo"] = ruta_completa
    
    # Preparar mensaje de confirmación
    mensaje_confirmacion = f"Tipo de operación: {datos_evidencia[user_id]['tipo_operacion']}\n" \
                         f"ID de operación: {op_id}\n" \
                         f"Archivo guardado como: {nombre_archivo}"
    
    # Añadir información de la carpeta
    folder_name = datos_evidencia[user_id]["folder_name"]
    mensaje_confirmacion += f"\nCarpeta: {folder_name}"
    
    # Añadir enlace de Drive si está disponible
    if DRIVE_ENABLED and drive_file_info and "drive_view_link" in datos_evidencia[user_id]:
        mensaje_confirmacion += f"\n\nEnlace en Drive: {datos_evidencia[user_id]['drive_view_link']}"
    
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
    
    # Procesar la ruta del archivo
    if "GoogleDrive:" in documento["ruta_archivo"]:
        # Es un archivo en Drive, mantener la cadena completa para referencia
        pass
    else:
        # Es un archivo local, construir la ruta correcta con la carpeta apropiada
        folder_name = documento["folder_name"]  # Extraída en seleccionar_tipo
        nombre_archivo = documento["nombre_archivo"]  # Extraído en subir_documento
        documento["ruta_archivo"] = f"{folder_name}/{nombre_archivo}"
    
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
