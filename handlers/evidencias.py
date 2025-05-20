"""
Manejador para el comando /evidencia.
Este comando permite seleccionar una compra y subir una evidencia de pago.
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
SELECCIONAR_COMPRA, SUBIR_DOCUMENTO, CONFIRMAR = range(3)

# Datos temporales
datos_evidencia = {}

# Asegurar que existe el directorio de uploads
if not os.path.exists(UPLOADS_FOLDER):
    os.makedirs(UPLOADS_FOLDER)
    logger.info(f"Directorio de uploads creado: {UPLOADS_FOLDER}")

async def evidencia_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Comando /evidencia para mostrar una lista seleccionable de compras registradas
    para adjuntar evidencias de pago
    """
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    logger.info(f"=== COMANDO /evidencia INICIADO por {username} (ID: {user_id}) ===")
    
    # Inicializar datos para este usuario
    datos_evidencia[user_id] = {
        "registrado_por": update.effective_user.username or update.effective_user.first_name
    }
    
    # Mostrar las compras recientes en un teclado seleccionable
    try:
        compras = get_all_data('compras')
        if compras:
            # Ordenar las compras por fecha (más recientes primero)
            compras_recientes = sorted(compras, key=lambda x: x.get('fecha', ''), reverse=True)[:10]
            
            # Crear teclado con las compras
            keyboard = []
            for compra in compras_recientes:
                compra_id = compra.get('id', 'Sin ID')
                proveedor = compra.get('proveedor', 'Proveedor desconocido')
                tipo_cafe = compra.get('tipo_cafe', 'Tipo desconocido')
                
                # Formatear fecha sin hora (solo YYYY-MM-DD)
                fecha_completa = compra.get('fecha', '')
                fecha_corta = fecha_completa.split(' ')[0] if ' ' in fecha_completa else fecha_completa
                
                # Crear botón con el formato: proveedor, tipo_cafe, fecha(sin hora), id
                boton_text = f"{proveedor}, {tipo_cafe}, {fecha_corta}, {compra_id}"
                keyboard.append([boton_text])
            
            keyboard.append(["❌ Cancelar"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            mensaje = "📋 *SELECCIONA UNA COMPRA PARA ADJUNTAR EVIDENCIA DE PAGO*\n\n"
            mensaje += "Formato: proveedor, tipo de café, fecha, ID"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
            
            # Redirigir al estado de selección de compra
            return SELECCIONAR_COMPRA
        else:
            await update.message.reply_text(
                "No hay compras registradas. Usa /compra para registrar una nueva compra.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error al obtener compras: {e}")
        await update.message.reply_text(
            "❌ Ocurrió un error al obtener las compras. Por favor, intenta nuevamente.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

async def seleccionar_compra(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de compra por el usuario"""
    user_id = update.effective_user.id
    respuesta = update.message.text.strip()
    
    # Verificar si el usuario cancela
    if respuesta.lower() == "❌ cancelar":
        await update.message.reply_text("Operación cancelada. Usa /evidencia para iniciar nuevamente.")
        return ConversationHandler.END
    
    # Extraer el ID de la compra (que está al final de la línea después de la última coma)
    partes = respuesta.split(',')
    if len(partes) < 4:
        await update.message.reply_text(
            "❌ Formato de selección inválido. Por favor, usa /evidencia para intentar nuevamente.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    compra_id = partes[-1].strip()
    logger.info(f"Usuario {user_id} seleccionó compra con ID: {compra_id}")
    
    # Guardar los datos de la compra
    datos_evidencia[user_id]["tipo_operacion"] = "COMPRA"
    datos_evidencia[user_id]["operacion_id"] = compra_id
    
    # Modo de almacenamiento
    almacenamiento = "Google Drive" if DRIVE_ENABLED else "almacenamiento local"
    
    # Informar al usuario que se ha seleccionado correctamente la compra
    await update.message.reply_text(
        f"Has seleccionado la compra con ID: {compra_id}\n\n"
        f"Ahora, envía la imagen de la evidencia de pago.\n"
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
            "⚠️ Por favor, envía una imagen de la evidencia de pago.\n"
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
                datos_evidencia[user_id]["drive_file_id"] = drive_file_info.get("id")
                datos_evidencia[user_id]["drive_view_link"] = drive_file_info.get("webViewLink")
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
    datos_evidencia[user_id]["ruta_archivo"] = ruta_completa
    
    # Preparar mensaje de confirmación
    mensaje_confirmacion = f"Tipo de operación: {datos_evidencia[user_id]['tipo_operacion']}\n" \
                         f"ID de operación: {op_id}\n" \
                         f"Archivo guardado como: {nombre_archivo}"
    
    # Añadir enlace de Drive si está disponible
    if DRIVE_ENABLED and drive_file_info and "drive_view_link" in datos_evidencia[user_id]:
        mensaje_confirmacion += f"\n\nEnlace en Drive: {datos_evidencia[user_id]['drive_view_link']}"
    
    # Teclado para confirmación
    keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Mostrar la imagen y solicitar confirmación
    # MODIFICADO: Evitamos usar parse_mode="Markdown" para evitar errores de formato
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
            SELECCIONAR_COMPRA: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_compra)],
            SUBIR_DOCUMENTO: [MessageHandler(filters.PHOTO, subir_documento)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    # Agregar el manejador al dispatcher
    application.add_handler(conv_handler)
    logger.info("Handler de evidencias registrado")