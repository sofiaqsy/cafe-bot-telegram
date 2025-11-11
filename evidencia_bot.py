#!/usr/bin/env python3
"""
Bot de Telegram independiente para manejo de evidencias de pago
Este bot es una solución temporal mientras se resuelven los problemas con el bot principal.
"""

import os
import sys
import logging
import uuid
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("evidencia_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Estados de la conversación
TIPO, ID_OPERACION, FOTO, CONFIRMAR = range(4)

# Directorio para guardar evidencias
UPLOADS_DIR = "evidencias_uploads"

# Asegurar que existe el directorio
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Función para inicio del bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /start."""
    user = update.effective_user
    logger.info(f"Usuario {user.username or user.first_name} (ID: {user.id}) inició el bot")
    
    await update.message.reply_html(
        f"¡Hola, {user.mention_html()}! 👋\n\n"
        "Soy el <b>Bot de Evidencias</b>, diseñado específicamente para ayudarte a registrar "
        "evidencias de pago para tus operaciones de café.\n\n"
        "Para comenzar, usa el comando /evidencia."
    )

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Maneja el comando /ayuda."""
    await update.message.reply_text(
        "📝 <b>GUÍA DE USO DEL BOT DE EVIDENCIAS</b>\n\n"
        "Este bot te ayuda a registrar evidencias de pago para tus operaciones de compra y venta de café.\n\n"
        "<b>Comandos disponibles:</b>\n"
        "/start - Inicia el bot\n"
        "/evidencia - Registra una nueva evidencia de pago\n"
        "/ayuda - Muestra este mensaje de ayuda\n\n"
        "<b>Proceso de registro:</b>\n"
        "1. Selecciona el tipo de operación (COMPRA o VENTA)\n"
        "2. Ingresa el ID de la operación\n"
        "3. Envía la foto de la evidencia de pago\n"
        "4. Confirma el registro\n\n"
        "Si necesitas ayuda adicional, contacta al administrador.",
        parse_mode="HTML"
    )

async def iniciar_evidencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el proceso de registro de evidencia."""
    user = update.effective_user
    logger.info(f"Usuario {user.username or user.first_name} (ID: {user.id}) inició registro de evidencia")
    
    # Limpiar datos anteriores
    context.user_data.clear()
    
    # Crear teclado con opciones
    keyboard = [["COMPRA"], ["VENTA"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_text(
        "📝 <b>REGISTRO DE EVIDENCIA DE PAGO</b>\n\n"
        "Paso 1 de 4: Selecciona el tipo de operación:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return TIPO

async def recibir_tipo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el tipo de operación y solicita el ID."""
    respuesta = update.message.text.strip()
    
    if respuesta.lower() == "❌ cancelar":
        return await cancelar(update, context)
    
    if respuesta not in ["COMPRA", "VENTA"]:
        await update.message.reply_text(
            "⚠️ Por favor, selecciona una opción válida: COMPRA o VENTA.",
            reply_markup=ReplyKeyboardMarkup([["COMPRA"], ["VENTA"], ["❌ Cancelar"]], one_time_keyboard=True, resize_keyboard=True)
        )
        return TIPO
    
    # Guardar el tipo seleccionado
    context.user_data["tipo"] = respuesta
    logger.info(f"Usuario {update.effective_user.id} seleccionó tipo: {respuesta}")
    
    await update.message.reply_text(
        f"<b>Tipo seleccionado:</b> {respuesta}\n\n"
        f"Paso 2 de 4: Por favor, ingresa el ID de la {respuesta.lower()}.\n"
        f"Este código lo recibiste cuando registraste la {respuesta.lower()}.\n\n"
        f"Ejemplo: C-2025-0042",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    
    return ID_OPERACION

async def recibir_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe el ID de operación y solicita la foto."""
    id_operacion = update.message.text.strip()
    
    # Validación básica del ID
    if len(id_operacion) < 3:
        await update.message.reply_text(
            "⚠️ El ID parece demasiado corto. Por favor, ingresa el ID completo."
        )
        return ID_OPERACION
    
    # Guardar el ID
    context.user_data["id_operacion"] = id_operacion
    logger.info(f"Usuario {update.effective_user.id} ingresó ID: {id_operacion}")
    
    await update.message.reply_text(
        f"<b>ID registrado:</b> {id_operacion}\n\n"
        f"Paso 3 de 4: Envía la foto de la evidencia de pago.\n"
        f"La imagen debe ser clara y mostrar todos los detalles relevantes.",
        parse_mode="HTML"
    )
    
    return FOTO

async def recibir_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibe la foto de evidencia y solicita confirmación."""
    # Verificar que se haya enviado una foto
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ Por favor, envía una imagen con la evidencia de pago."
        )
        return FOTO
    
    # Obtener la foto de mejor calidad (última en la lista)
    photo = update.message.photo[-1]
    file_id = photo.file_id
    
    # Guardar datos de la foto
    context.user_data["foto_id"] = file_id
    
    # Generar identificador único para esta evidencia
    evidencia_id = f"E-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    context.user_data["evidencia_id"] = evidencia_id
    
    # Preparar resumen
    tipo = context.user_data["tipo"]
    id_operacion = context.user_data["id_operacion"]
    
    logger.info(f"Usuario {update.effective_user.id} subió foto con ID: {file_id}")
    
    # Mostrar resumen y solicitar confirmación
    keyboard = [["✅ Confirmar"], ["❌ Cancelar"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    await update.message.reply_photo(
        photo=file_id,
        caption=f"📝 <b>RESUMEN DE EVIDENCIA</b>\n\n"
                f"<b>ID Evidencia:</b> {evidencia_id}\n"
                f"<b>Tipo operación:</b> {tipo}\n"
                f"<b>ID operación:</b> {id_operacion}\n\n"
                f"¿Deseas confirmar el registro de esta evidencia?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    
    return CONFIRMAR

async def confirmar_evidencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la confirmación y guarda la evidencia."""
    respuesta = update.message.text.strip().lower()
    
    if respuesta != "✅ confirmar" and not respuesta.startswith("confirm"):
        return await cancelar(update, context)
    
    # Obtener datos guardados
    evidencia_id = context.user_data["evidencia_id"]
    tipo = context.user_data["tipo"]
    id_operacion = context.user_data["id_operacion"]
    foto_id = context.user_data["foto_id"]
    
    # Guardar la imagen localmente
    try:
        file = await context.bot.get_file(foto_id)
        file_path = os.path.join(UPLOADS_DIR, f"{evidencia_id}.jpg")
        await file.download_to_drive(file_path)
        logger.info(f"Evidencia guardada en: {file_path}")
        
        # Guardar registro en CSV
        csv_path = os.path.join(UPLOADS_DIR, "evidencias.csv")
        
        # Verificar si el archivo existe, si no, crear con encabezados
        if not os.path.exists(csv_path):
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write("fecha,evidencia_id,tipo,operacion_id,usuario_id,usuario_nombre,foto_id,ruta_archivo\n")
        
        # Añadir registro
        with open(csv_path, 'a', encoding='utf-8') as f:
            fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            usuario_id = update.effective_user.id
            usuario_nombre = update.effective_user.username or update.effective_user.first_name
            f.write(f'"{fecha}","{evidencia_id}","{tipo}","{id_operacion}","{usuario_id}","{usuario_nombre}","{foto_id}","{file_path}"\n')
        
        # Notificar éxito
        await update.message.reply_text(
            f"✅ <b>¡Evidencia registrada exitosamente!</b>\n\n"
            f"<b>ID de evidencia:</b> {evidencia_id}\n"
            f"<b>Tipo:</b> {tipo}\n"
            f"<b>ID operación:</b> {id_operacion}\n\n"
            f"Un administrador procesará tu evidencia pronto. Si necesitas registrar otra evidencia, usa el comando /evidencia nuevamente.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        
        # Limpiar datos de usuario
        context.user_data.clear()
        
        return ConversationHandler.END
    
    except Exception as e:
        logger.error(f"Error al guardar evidencia: {e}")
        await update.message.reply_text(
            "❌ <b>Error al guardar la evidencia</b>\n\n"
            "Ha ocurrido un problema al procesar tu solicitud. Por favor, intenta nuevamente o contacta al administrador.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela el proceso de registro de evidencia."""
    logger.info(f"Usuario {update.effective_user.id} canceló el proceso")
    
    # Limpiar datos de usuario
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ Operación cancelada.\n\n"
        "Usa /evidencia cuando quieras registrar una evidencia de pago.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

def main() -> None:
    """Inicia el bot."""
    # Obtener el token de una variable de entorno o de un archivo
    TOKEN = os.environ.get("TELEGRAM_BOT_EVIDENCIA_TOKEN")
    
    if not TOKEN:
        try:
            with open("token_evidencia.txt", "r") as f:
                TOKEN = f.read().strip()
        except:
            logger.error("No se pudo obtener el token del bot. Verifica las variables de entorno o el archivo token_evidencia.txt")
            sys.exit(1)
    
    # Crear la aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Registrar comandos básicos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("help", ayuda))
    
    # Crear manejador de conversación para el registro de evidencias
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("evidencia", iniciar_evidencia)],
        states={
            TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_tipo)],
            ID_OPERACION: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_id)],
            FOTO: [MessageHandler(filters.PHOTO, recibir_foto)],
            CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar_evidencia)],
        },
        fallbacks=[CommandHandler("cancelar", cancelar)],
    )
    
    application.add_handler(conv_handler)
    
    # Iniciar el bot
    logger.info("Bot de evidencias iniciado")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()