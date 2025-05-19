import os
import logging
import requests
import traceback
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Configuración de logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Asegurarse de que los logs de las bibliotecas no sean demasiado verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Cargar variables de entorno directamente
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Importar el resto de módulos después de cargar las variables de entorno
from utils.sheets import initialize_sheets

# Importar handlers
from handlers.start import start_command, help_command
from handlers.compras import register_compras_handlers
from handlers.proceso import register_proceso_handlers
from handlers.gastos import register_gastos_handlers
from handlers.ventas import register_ventas_handlers
from handlers.reportes import register_reportes_handlers
from handlers.pedidos import register_pedidos_handlers
from handlers.adelantos import register_adelantos_handlers
from handlers.compra_adelanto import register_compra_adelanto_handlers
from handlers.almacen import register_almacen_handlers

# AÑADIDO: Importación para el handler de documentos
try:
    logger.info("Intentando importar el módulo documents...")
    from handlers.documents import register_documents_handlers
    logger.info("Módulo documents importado correctamente")
    documents_importado = True
except Exception as e:
    logger.error(f"Error al importar el módulo documents: {e}")
    logger.error(traceback.format_exc())
    documents_importado = False

# AÑADIDO: Funciones simples de emergencia para el comando /documento
async def documento_simple(update, context):
    """Función simple para manejar el comando /documento cuando el módulo principal falla"""
    try:
        user = update.effective_user
        logger.info(f"Comando /documento ejecutado por {user.username or user.first_name} (ID: {user.id})")
        
        await update.message.reply_text(
            "📝 *SISTEMA ALTERNATIVO DE EVIDENCIAS DE PAGO*\n\n"
            "Para registrar una evidencia de pago, sigue estos pasos:\n\n"
            "1. Toma una foto clara del comprobante de pago\n"
            "2. Añade a la imagen una descripción que incluya:\n"
            "   - Tipo: COMPRA o VENTA\n"
            "   - ID de la operación (ejemplo: C-2025-0042)\n"
            "   - Breve descripción de la operación\n\n"
            "Ejemplo de descripción:\n"
            "`Tipo: COMPRA\nID: C-2025-0042\nPago a proveedor Juan Pérez por 50kg de café`\n\n"
            "Un administrador procesará tu evidencia manualmente.",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error en documento_simple: {e}")
        await update.message.reply_text(
            "❌ Ha ocurrido un error al procesar tu solicitud. Por favor, contacta al administrador."
        )

async def procesar_foto_evidencia(update, context):
    """Procesa fotos enviadas como posibles evidencias de pago"""
    try:
        user = update.effective_user
        caption = update.message.caption or ""
        
        # Verificar si parece una evidencia de pago
        keywords = ["compra", "venta", "pago", "evidencia", "documento"]
        if any(keyword in caption.lower() for keyword in keywords):
            logger.info(f"Posible evidencia recibida de {user.username or user.first_name} (ID: {user.id})")
            
            # Guardar la foto
            photo = update.message.photo[-1]
            file_id = photo.file_id
            file = await context.bot.get_file(file_id)
            
            # Crear directorio de uploads si no existe
            uploads_dir = os.getenv("UPLOADS_FOLDER", "uploads")
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Generar nombre único
            import uuid
            from datetime import datetime
            filename = f"evidencia_{user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.jpg"
            filepath = os.path.join(uploads_dir, filename)
            
            # Descargar archivo
            await file.download_to_drive(filepath)
            
            # Extraer información de la descripción
            tipo = "No especificado"
            id_op = "No especificado"
            
            if "tipo:" in caption.lower():
                tipo_text = caption.lower().split("tipo:")[1].split("\n")[0].strip()
                if "compra" in tipo_text:
                    tipo = "COMPRA"
                elif "venta" in tipo_text:
                    tipo = "VENTA"
            
            if "id:" in caption.lower():
                id_op = caption.lower().split("id:")[1].split("\n")[0].strip()
            
            # Registrar en log
            logger.info(f"Evidencia guardada: {filepath}")
            logger.info(f"Información: Tipo={tipo}, ID={id_op}, Usuario={user.username or user.first_name}")
            
            # Confirmar al usuario
            await update.message.reply_text(
                f"✅ *Evidencia registrada correctamente*\n\n"
                f"Archivo: {filename}\n"
                f"Tipo: {tipo}\n"
                f"ID operación: {id_op}\n\n"
                f"Un administrador procesará tu evidencia manualmente.",
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Error en procesar_foto_evidencia: {e}")
        logger.error(traceback.format_exc())

def eliminar_webhook():
    """Elimina cualquier webhook configurado antes de iniciar el polling"""
    try:
        logger.info("Eliminando webhook existente...")
        url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook"
        logger.info(f"Realizando solicitud a: {url.replace(TOKEN, TOKEN[:5] + '...')}")
        
        response = requests.get(url)
        logger.info(f"Respuesta del servidor: Código {response.status_code}")
        
        if response.status_code == 200 and response.json().get("ok"):
            logger.info("Webhook eliminado correctamente")
            return True
        else:
            logger.error(f"Error al eliminar webhook: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Excepción al eliminar webhook: {e}")
        return False

def main():
    """Iniciar el bot con polling para Heroku"""
    logger.info("Iniciando bot de Telegram para Gestión de Café en Heroku")
    
    # Verificar el token (seguro, solo muestra los primeros 5 caracteres)
    if not TOKEN:
        logger.error("¡ERROR! No se encontró el token de Telegram en las variables de entorno")
        return
    else:
        logger.info(f"Token encontrado (primeros 5 caracteres): {TOKEN[:5]}...")
    
    # Eliminar webhook existente
    if not eliminar_webhook():
        logger.warning("No se pudo eliminar el webhook. Intentando continuar de todos modos...")
    
    # Inicializar Google Sheets
    try:
        logger.info("Inicializando Google Sheets...")
        initialize_sheets()
        logger.info("Google Sheets inicializado correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar Google Sheets: {e}")
        logger.warning("El bot continuará funcionando, pero los datos no se guardarán en Google Sheets")
    
    # Crear la aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Registrar comandos básicos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Registrar handlers específicos
    register_compras_handlers(application)
    register_proceso_handlers(application)
    register_gastos_handlers(application)
    register_ventas_handlers(application)
    register_reportes_handlers(application)
    register_pedidos_handlers(application)
    register_adelantos_handlers(application)
    register_compra_adelanto_handlers(application)
    register_almacen_handlers(application)
    
    # AÑADIDO: Intentar registrar el handler de documentos
    documento_handler_registrado = False
    
    # Intento 1: Usar el módulo documents si está disponible
    if documents_importado:
        try:
            logger.info("Registrando handler de documentos...")
            register_documents_handlers(application)
            logger.info("Handler de documentos registrado correctamente")
            documento_handler_registrado = True
        except Exception as e:
            logger.error(f"Error al registrar handler de documentos: {e}")
            logger.error(traceback.format_exc())
    else:
        logger.warning("No se importó el módulo documents, se usará el handler simple")
    
    # Intento 2: Si el handler principal falla, usar la versión simple
    if not documento_handler_registrado:
        try:
            logger.info("Registrando handler simple para documentos...")
            
            # Registrar comando /documento
            application.add_handler(CommandHandler("documento", documento_simple))
            
            # Registrar handler para procesar fotos
            application.add_handler(MessageHandler(filters.PHOTO, procesar_foto_evidencia))
            
            logger.info("Handler simple para documentos registrado correctamente")
            documento_handler_registrado = True
        except Exception as e:
            logger.error(f"Error al registrar handler simple para documentos: {e}")
            logger.error(traceback.format_exc())
    
    # Registrar comando de prueba
    async def test_bot(update, context):
        await update.message.reply_text(
            "✅ El bot está funcionando correctamente.\n\n"
            f"Sistema de documentos: {'ACTIVO' if documento_handler_registrado else 'INACTIVO'}"
        )
    
    application.add_handler(CommandHandler("test_bot", test_bot))
    
    # IMPORTANTE: Usar POLLING, no webhook
    logger.info("Bot iniciado en modo POLLING. Esperando comandos...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()