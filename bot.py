import os
import logging
import traceback
import requests
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

# Configuración de logging avanzada
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG  # Cambiado a DEBUG para más detalles
)
logger = logging.getLogger(__name__)

# Asegurarse de que los logs de las bibliotecas no sean demasiado verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Importar configuración
from config import TOKEN, sheets_configured
from utils.sheets import initialize_sheets

# Log inicial
logger.info("=== INICIANDO BOT DE CAFE - MODO DEBUG ===")

# Intentar importar handlers con captura de errores
try:
    logger.info("Importando handlers...")
    
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
    
    # Import del NUEVO handler de emergencia para documentos
    try:
        logger.info("Importando módulo de emergencia para documentos...")
        from handlers.documento_emergency import register_documento_emergency
        logger.info("Módulo de emergencia para documentos importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo de emergencia para documentos: {e}")
        logger.error(traceback.format_exc())
        register_documento_emergency = None
    
    # Import especial para documents con captura de error
    try:
        logger.info("Importando módulo documents...")
        from handlers.documents import register_documents_handlers
        logger.info("Módulo documents importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo documents: {e}")
        logger.error(traceback.format_exc())
        register_documents_handlers = None
    
    # Import especial del módulo simple_document como backup para /documento
    try:
        logger.info("Importando módulo simple_document (backup)...")
        from handlers.simple_document import simple_documento_command, simple_cancelar
        logger.info("Módulo simple_document importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo simple_document: {e}")
        logger.error(traceback.format_exc())
        simple_documento_command = None
        simple_cancelar = None
    
    # Import del módulo de diagnóstico
    try:
        logger.info("Importando módulo diagnostico...")
        from handlers.diagnostico import register_diagnostico_handlers
        logger.info("Módulo diagnostico importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo diagnostico: {e}")
        logger.error(traceback.format_exc())
        register_diagnostico_handlers = None
    
    logger.info("Todos los handlers importados correctamente")
    
except Exception as e:
    logger.error(f"ERROR importando handlers: {e}")
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
        logger.error(traceback.format_exc())
        return False

def main():
    """Iniciar el bot"""
    logger.info("Iniciando bot de Telegram para Gestión de Café")
    
    # Verificar la configuración de Google Sheets
    if sheets_configured:
        logger.info("Inicializando Google Sheets...")
        try:
            initialize_sheets()
            logger.info("Google Sheets inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar Google Sheets: {e}")
            logger.error(traceback.format_exc())
            logger.warning("El bot continuará funcionando, pero los datos no se guardarán en Google Sheets")
    else:
        logger.warning("Google Sheets no está configurado. Los datos no se guardarán correctamente.")
        logger.info("Asegúrate de configurar SPREADSHEET_ID y GOOGLE_CREDENTIALS en las variables de entorno")
    
    # Imprimir variables de entorno (solo para depuración, sin mostrar valores sensibles)
    env_vars = [
        "TELEGRAM_BOT_TOKEN", 
        "SPREADSHEET_ID", 
        "GOOGLE_CREDENTIALS",
        "DRIVE_ENABLED",
        "DRIVE_EVIDENCIAS_ROOT_ID",
        "DRIVE_EVIDENCIAS_COMPRAS_ID",
        "DRIVE_EVIDENCIAS_VENTAS_ID"
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            if var in ["GOOGLE_CREDENTIALS", "TELEGRAM_BOT_TOKEN"]:
                # Mostrar solo los primeros 10 caracteres del token/credenciales, para verificar
                logger.info(f"Variable de entorno {var} está configurada: {value[:10]}...")
            else:
                logger.info(f"Variable de entorno {var} está configurada: {value}")
        else:
            logger.warning(f"Variable de entorno {var} NO está configurada")
    
    # Crear la aplicación
    try:
        logger.info("Creando aplicación con TOKEN...")
        application = Application.builder().token(TOKEN).build()
        logger.info("Aplicación creada correctamente")
    except Exception as e:
        logger.error(f"ERROR CRÍTICO al crear aplicación: {e}")
        logger.error(traceback.format_exc())
        return
    
    # Registrar comandos básicos
    try:
        logger.info("Registrando comandos básicos...")
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("ayuda", help_command))
        application.add_handler(CommandHandler("help", help_command))
        logger.info("Comandos básicos registrados correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comandos básicos: {e}")
        logger.error(traceback.format_exc())
    
    # ----- PRIORIDAD ALTA: Registrar PRIMERO el sistema de emergencia -----
    documento_emergency_registrado = False
    
    if register_documento_emergency is not None:
        try:
            logger.info("ALTA PRIORIDAD: Registrando handler de emergencia para documentos...")
            register_documento_emergency(application)
            logger.info("Handler de emergencia para documentos registrado con éxito")
            documento_emergency_registrado = True
        except Exception as e:
            logger.error(f"Error al registrar handler de emergencia para documentos: {e}")
            logger.error(traceback.format_exc())
    
    # Registrar handlers específicos
    handlers_registrados = 0
    handlers_fallidos = 0
    
    # Lista de funciones de registro de handlers
    handler_functions = [
        ("compras", register_compras_handlers),
        ("proceso", register_proceso_handlers),
        ("gastos", register_gastos_handlers),
        ("ventas", register_ventas_handlers),
        ("reportes", register_reportes_handlers),
        ("pedidos", register_pedidos_handlers),
        ("adelantos", register_adelantos_handlers),
        ("compra_adelanto", register_compra_adelanto_handlers),
        ("almacen", register_almacen_handlers)
    ]
    
    # Registrar cada handler con manejo de excepciones individual
    for name, handler_func in handler_functions:
        try:
            logger.info(f"Registrando handler: {name}...")
            handler_func(application)
            logger.info(f"Handler {name} registrado correctamente")
            handlers_registrados += 1
        except Exception as e:
            logger.error(f"Error al registrar handler {name}: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    
    # IMPLEMENTACIÓN ROBUSTA DEL HANDLER DE DOCUMENTOS (si aún no se ha registrado la emergencia)
    if not documento_emergency_registrado:
        documento_handler_registrado = False
        
        # Intento 1: Registrar el handler completo desde el módulo documents
        if register_documents_handlers is not None:
            try:
                logger.info("Intento 1: Registrando handler de documentos completo...")
                register_documents_handlers(application)
                logger.info("Handler de documentos registrado correctamente")
                handlers_registrados += 1
                documento_handler_registrado = True
            except Exception as e:
                logger.error(f"Error al registrar handler de documentos completo: {e}")
                logger.error(traceback.format_exc())
                handlers_fallidos += 1
        else:
            logger.error("No se pudo registrar el handler de documentos: Módulo no disponible")
            handlers_fallidos += 1
        
        # Intento 2: Si falló el primero, registrar directamente el comando desde handlers.documents
        if not documento_handler_registrado:
            try:
                logger.info("Intento 2: Importando documento_command desde handlers.documents...")
                from handlers.documents import documento_command, cancelar
                
                logger.info("Registrando CommandHandler directo para /documento desde módulo documents...")
                application.add_handler(CommandHandler("documento", documento_command))
                application.add_handler(CommandHandler("cancelar", cancelar))
                logger.info("CommandHandler para /documento desde módulo documents registrado correctamente")
                handlers_registrados += 1
                documento_handler_registrado = True
            except Exception as e:
                logger.error(f"Error al registrar CommandHandler directo para /documento desde module documents: {e}")
                logger.error(traceback.format_exc())
        
        # Intento 3: Si todavía no se ha registrado, usar la implementación simplificada
        if not documento_handler_registrado and simple_documento_command is not None:
            try:
                logger.info("Intento 3: Registrando implementación simplificada para /documento...")
                
                # Registrar el CommandHandler simple
                application.add_handler(CommandHandler("documento", simple_documento_command))
                
                # Crear y registrar un ConversationHandler sencillo
                SELECCIONAR_TIPO, SELECCIONAR_ID, SUBIR_DOCUMENTO, CONFIRMAR = range(4)
                simple_conv_handler = ConversationHandler(
                    entry_points=[],  # No entry points, solo como fallback
                    states={
                        SELECCIONAR_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, simple_cancelar)],
                        SELECCIONAR_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, simple_cancelar)],
                        SUBIR_DOCUMENTO: [MessageHandler(filters.PHOTO, simple_cancelar)],
                        CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, simple_cancelar)],
                    },
                    fallbacks=[CommandHandler("cancelar", simple_cancelar)],
                )
                
                application.add_handler(simple_conv_handler)
                application.add_handler(CommandHandler("cancelar", simple_cancelar))  # También registrar cancelar directo
                
                logger.info("Implementación simplificada para /documento registrada correctamente")
                handlers_registrados += 1
                documento_handler_registrado = True
            except Exception as e:
                logger.error(f"Error al registrar implementación simplificada para /documento: {e}")
                logger.error(traceback.format_exc())
        
        # Intento 4: Último recurso, registrar un handler simple que solo muestra un mensaje
        if not documento_handler_registrado:
            try:
                logger.info("Intento 4: Registrando handler de último recurso para /documento...")
                
                async def documento_fallback(update, context):
                    await update.message.reply_text(
                        "⚠️ El sistema de documentos está en mantenimiento. Por favor, intenta más tarde.\n\n"
                        "Para cargar evidencia de pago, envía directamente la imagen y describe a qué operación corresponde."
                    )
                
                application.add_handler(CommandHandler("documento", documento_fallback))
                logger.info("Handler de último recurso para /documento registrado correctamente")
                handlers_registrados += 1
                documento_handler_registrado = True
            except Exception as e:
                logger.error(f"Error al registrar handler de último recurso para /documento: {e}")
                logger.error(traceback.format_exc())
    else:
        logger.info("No se registraron handlers adicionales para /documento porque ya está activo el sistema de emergencia")
    
    # Registrar handler de diagnóstico (con verificación especial)
    if register_diagnostico_handlers is not None:
        try:
            logger.info("Registrando handler de diagnóstico...")
            register_diagnostico_handlers(application)
            logger.info("Handler de diagnóstico registrado correctamente")
            handlers_registrados += 1
        except Exception as e:
            logger.error(f"Error al registrar handler de diagnóstico: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    else:
        logger.error("No se pudo registrar el handler de diagnóstico: Módulo no disponible")
        handlers_fallidos += 1
    
    # Registrar comando de test directo (sin usar el módulo documents)
    try:
        logger.info("Registrando comando de test directo...")
        application.add_handler(
            CommandHandler("test_bot", 
                lambda update, context: update.message.reply_text(
                    "\ud83d\udc4d El bot está funcionando correctamente y puede recibir comandos.\n\n"
                    "Usa /diagnostico para obtener más información sobre el estado del bot."
                )
            )
        )
        logger.info("Comando de test directo registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comando de test directo: {e}")
        logger.error(traceback.format_exc())
    
    # Registrar un manejador para informar sobre el sistema de emergencia si alguien menciona documento
    try:
        logger.info("Registrando manejador para informar sobre el sistema de emergencia...")
        
        async def informar_sistema_emergencia(update, context):
            # Solo responder si se mencionan estas palabras clave y no es un comando
            text = update.message.text.lower()
            if any(palabra in text for palabra in ["documento", "documentos", "evidencia", "comprobante", "pago"]) and not text.startswith('/'):
                await update.message.reply_text(
                    "💡 ¿Necesitas subir evidencia de pago?\n\n"
                    "Usa el comando /evidencia para acceder al sistema alternativo de documentos."
                )
        
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                informar_sistema_emergencia
            )
        )
        logger.info("Manejador para informar sobre sistema de emergencia registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar manejador para informar sobre sistema de emergencia: {e}")
        logger.error(traceback.format_exc())
    
    # Registrar CommandHandler directo para actualizar comandos
    try:
        logger.info("Registrando comando para actualizar comandos en BotFather...")
        
        async def actualizar_comandos_botfather(update, context):
            """Comando de administrador para actualizar los comandos disponibles en BotFather"""
            user_id = update.effective_user.id
            
            # Este comando solo debe ser usado por administradores
            admins = [12503633]  # Ejemplo: IDs de los administradores
            if user_id not in admins:
                await update.message.reply_text("⚠️ Este comando es solo para administradores.")
                return
            
            try:
                # Lista de comandos actualizada
                commands = [
                    {"command": "start", "description": "Iniciar el bot"},
                    {"command": "ayuda", "description": "Mostrar la ayuda"},
                    {"command": "compra", "description": "Registrar compra de café"},
                    {"command": "compra_adelanto", "description": "Compra con adelanto"},
                    {"command": "proceso", "description": "Registrar procesamiento"},
                    {"command": "venta", "description": "Registrar venta"},
                    {"command": "reporte", "description": "Ver reportes"},
                    {"command": "gasto", "description": "Registrar gasto"},
                    {"command": "adelanto", "description": "Registrar adelanto a proveedor"},
                    {"command": "adelantos", "description": "Ver adelantos vigentes"},
                    {"command": "evidencia", "description": "Cargar evidencia de pago"},
                    {"command": "pedido", "description": "Registrar pedido de cliente"},
                    {"command": "pedidos", "description": "Ver pedidos pendientes"},
                    {"command": "almacen", "description": "Gestionar almacén central"},
                    {"command": "test_bot", "description": "Probar si el bot responde"}
                ]
                
                # Realizar la petición a la API
                url = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"
                response = requests.post(url, json={"commands": commands})
                
                if response.status_code == 200 and response.json().get("ok"):
                    await update.message.reply_text("✅ Comandos actualizados correctamente en BotFather.")
                else:
                    await update.message.reply_text(f"❌ Error al actualizar comandos: {response.text}")
            
            except Exception as e:
                logger.error(f"Error al actualizar comandos: {e}")
                logger.error(traceback.format_exc())
                await update.message.reply_text(f"❌ Error al actualizar comandos: {str(e)}")
        
        application.add_handler(CommandHandler("actualizar_comandos", actualizar_comandos_botfather))
        logger.info("Comando para actualizar comandos en BotFather registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comando para actualizar comandos: {e}")
        logger.error(traceback.format_exc())
    
    # Resumen de registro de handlers
    logger.info(f"Resumen de registro de handlers: {handlers_registrados} éxitos, {handlers_fallidos} fallos")
    logger.info(f"Estado del handler de emergencia para documentos: {'ACTIVO' if documento_emergency_registrado else 'INACTIVO'}")
    
    # Si todos los handlers fallaron, salir
    if handlers_registrados == 0 and handlers_fallidos > 0:
        logger.error("No se pudo registrar ningún handler. Finalizando inicialización.")
        return
    
    # Eliminar webhook existente
    if not eliminar_webhook():
        logger.warning("No se pudo eliminar el webhook. Intentando continuar de todos modos...")
    
    # Iniciar el bot
    try:
        logger.info("Bot iniciado. Esperando comandos...")
        application.run_polling(drop_pending_updates=True)
    except Exception as e:
        logger.error(f"Error al iniciar el bot: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error fatal en la ejecución del bot: {e}")
        logger.error(traceback.format_exc())