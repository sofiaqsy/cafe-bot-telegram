"""
Manejador para el comando /evidencia.
Este comando permite seleccionar una operación (compra, venta, adelanto o gasto) y subir una evidencia.
"""

import logging
import os
import uuid
import traceback
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, ConversationHandler
from utils.sheets import get_all_data, append_data as append_sheets, generate_unique_id, get_filtered_data
from utils.helpers import get_now_peru, format_date_for_sheets
from utils.drive import upload_file_to_drive, setup_drive_folders
from config import (
    UPLOADS_FOLDER, 
    DRIVE_ENABLED, 
    DRIVE_EVIDENCIAS_COMPRAS_ID, 
    DRIVE_EVIDENCIAS_VENTAS_ID, 
    DRIVE_EVIDENCIAS_ROOT_ID,
    DRIVE_EVIDENCIAS_ADELANTOS_ID,
    DRIVE_EVIDENCIAS_GASTOS_ID,
    DRIVE_EVIDENCIAS_CAPITALIZACION_ID
)

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
CAPITALIZACION_FOLDER = os.path.join(UPLOADS_FOLDER, "capitalizacion")  # Nueva carpeta para capitalización

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

if not os.path.exists(CAPITALIZACION_FOLDER):
    os.makedirs(CAPITALIZACION_FOLDER)
    logger.info(f"Directorio para evidencias de capitalización creado: {CAPITALIZACION_FOLDER}")

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

def parse_fecha_sheets(fecha_str):
    """
    Convierte una fecha en formato de Google Sheets a un objeto datetime.
    Maneja varios formatos posibles.
    """
    try:
        # Limpiar el formato protegido de sheets si es necesario
        if fecha_str.startswith("'"):
            fecha_str = fecha_str[1:]
        
        # Intentar con diferentes formatos
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"]:
            try:
                return datetime.strptime(fecha_str, fmt)
            except ValueError:
                continue
                
        # Si ninguno funciona, devolver una fecha muy antigua para que se ordene al final
        logger.warning(f"No se pudo parsear la fecha: {fecha_str}")
        return datetime(1900, 1, 1)
    except Exception as e:
        logger.error(f"Error al parsear fecha '{fecha_str}': {e}")
        return datetime(1900, 1, 1)

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
        ["💼 Capitalización"],  # Nueva opción para capitalización
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
    elif "capitalización" in respuesta.lower() or "capitalizacion" in respuesta.lower():
        tipo_operacion = "CAPITALIZACION"
        operacion_plural = "capitalizacion"
        datos_evidencia[user_id]["tipo_operacion"] = tipo_operacion
        datos_evidencia[user_id]["folder_name"] = "capitalizacion"  # Guardar el nombre de la carpeta
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
            # Registrar la cantidad total de operaciones para información
            total_operaciones = len(operaciones)
            logger.info(f"Total de {operacion_plural} encontradas: {total_operaciones}")
            
            # Ordenar las operaciones por fecha (más recientes primero)
            # Mejora: Usar un parse de fecha más robusto para manejar diferentes formatos
            try:
                # Ordenar primero por fecha
                operaciones_ordenadas = sorted(
                    operaciones, 
                    key=lambda x: parse_fecha_sheets(x.get('fecha', '1900-01-01')), 
                    reverse=True
                )
                
                # Log para verificar el ordenamiento
                if operaciones_ordenadas and len(operaciones_ordenadas) > 0:
                    logger.info(f"Primera operación ordenada: {operaciones_ordenadas[0].get('id', 'Sin ID')} - Fecha: {operaciones_ordenadas[0].get('fecha', 'Sin fecha')}")
                    if len(operaciones_ordenadas) > 1:
                        logger.info(f"Segunda operación ordenada: {operaciones_ordenadas[1].get('id', 'Sin ID')} - Fecha: {operaciones_ordenadas[1].get('fecha', 'Sin fecha')}")
            except Exception as e:
                logger.error(f"Error al ordenar operaciones por fecha: {e}")
                logger.error(traceback.format_exc())
                # Si hay error al ordenar, usar las operaciones sin ordenar
                operaciones_ordenadas = operaciones
                logger.info("Usando operaciones sin ordenar debido al error")
            
            # Limitar a las últimas operaciones para el teclado
            operaciones_recientes = operaciones_ordenadas[:MAX_OPERACIONES]
            logger.info(f"Mostrando {len(operaciones_recientes)} {operacion_plural} recientes de un total de {total_operaciones}")
            
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
                    # Formato para compras
                    proveedor = operacion.get('proveedor', 'Proveedor desconocido')
                    tipo_cafe = operacion.get('tipo_cafe', 'Tipo desconocido')
                    total = operacion.get('preciototal', '0')
                    boton_text = f"{proveedor} | S/ {total} | {tipo_cafe} | ID:{operacion_id}"
                elif tipo_operacion == "VENTA":
                    # Para ventas
                    cliente = operacion.get('cliente', 'Cliente desconocido')
                    producto = operacion.get('producto', 'Producto desconocido')
                    boton_text = f"{cliente} | {producto} | ID:{operacion_id}"
                elif tipo_operacion == "ADELANTO":
                    # Para adelantos
                    proveedor = operacion.get('proveedor', 'Proveedor desconocido')
                    monto = operacion.get('monto', '0')
                    boton_text = f"{proveedor} | S/ {monto} | ID:{operacion_id}"
                elif tipo_operacion == "CAPITALIZACION":
                    # Para capitalización
                    origen = operacion.get('origen', 'Origen desconocido')
                    destino = operacion.get('destino', 'Destino desconocido')
                    monto = operacion.get('monto', '0')
                    boton_text = f"{origen} | S/ {monto} | {destino} | ID:{operacion_id}"
                
                keyboard.append([boton_text])
            
            keyboard.append(["❌ Cancelar"])
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            mensaje = f"📋 *SELECCIONA UNA {tipo_operacion} PARA ADJUNTAR EVIDENCIA*\n\n"
            
            # Indicar cuántas operaciones se están mostrando de un total
            if total_operaciones > MAX_OPERACIONES:
                mensaje += f"Mostrando las {len(operaciones_recientes)} {operacion_plural} más recientes de un total de {total_operaciones}"
            else:
                mensaje += f"Mostrando {len(operaciones_recientes)} {operacion_plural} disponibles"
            
            await update.message.reply_text(mensaje, parse_mode="Markdown", reply_markup=reply_markup)
            
            # Redirigir al estado de selección de operación
            return SELECCIONAR_OPERACION
        else:
            # Para capitalización
            if tipo_operacion == "CAPITALIZACION":
                comando_registro = "/capitalizacion"
            else:
                comando_registro = f"/{operacion_plural[:-1]}"  # /compra, /venta, /adelanto, /gasto
                
            await update.message.reply_text(
                f"No hay {operacion_plural} registradas. Usa {comando_registro} para registrar una nueva operación.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error al obtener {operacion_plural}: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text(
            f"❌ Ocurrió un error al obtener las {operacion_plural}. Por favor, intenta nuevamente.\n\nError: {str(e)}",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

# Aquí continúa el resto del archivo...

# Función para obtener el folder_id adecuado según el tipo de operación
def get_folder_id_for_operation(tipo_operacion):
    """Devuelve el ID de carpeta de Drive apropiado según el tipo de operación"""
    if tipo_operacion == "COMPRA":
        return DRIVE_EVIDENCIAS_COMPRAS_ID
    elif tipo_operacion == "VENTA":
        return DRIVE_EVIDENCIAS_VENTAS_ID
    elif tipo_operacion == "ADELANTO":
        return DRIVE_EVIDENCIAS_ADELANTOS_ID
    elif tipo_operacion == "GASTO":
        return DRIVE_EVIDENCIAS_GASTOS_ID
    elif tipo_operacion == "CAPITALIZACION":
        return DRIVE_EVIDENCIAS_CAPITALIZACION_ID
    else:
        # Si no se reconoce el tipo, usar la carpeta raíz
        return DRIVE_EVIDENCIAS_ROOT_ID

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
    
    # Para gastos múltiples, usar un identificador único en lugar de todos los IDs
    if tipo_op.upper() == "GASTO" and "+" in op_id:
        gasto_count = len(op_id.split("+"))
        nombre_archivo = f"{tipo_op}_multiple_{gasto_count}_gastos_S{monto}_{uuid.uuid4().hex[:8]}.jpg"
    else:
        nombre_archivo = f"{tipo_op}_{op_id}_S{monto}_{uuid.uuid4().hex[:8]}.jpg"
    
    # Guardar el nombre del archivo
    datos_evidencia[user_id]["nombre_archivo"] = nombre_archivo
    
    # Determinar la carpeta local según el tipo de operación
    folder_name = datos_evidencia[user_id]["folder_name"]
    local_folder = os.path.join(UPLOADS_FOLDER, folder_name)
    
    # Para Google Drive, usar la carpeta específica según el tipo de operación
    folder_id = None
    if DRIVE_ENABLED:
        folder_id = get_folder_id_for_operation(tipo_op.upper())
        if not folder_id:
            logger.warning(f"No se encontró ID de carpeta para {tipo_op.upper()}, usando carpeta raíz")
            folder_id = DRIVE_EVIDENCIAS_ROOT_ID
    
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

# El resto del archivo sigue igual...

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