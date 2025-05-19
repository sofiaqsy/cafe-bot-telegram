import os
import logging
import traceback
import requests
import sys
import importlib
from datetime import datetime
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters

# Configuración de logging avanzada
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
logging.basicConfig(
    format=LOG_FORMAT,
    level=logging.DEBUG,
    handlers=[
        logging.FileHandler("bot_debug.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Asegurarse de que los logs de las bibliotecas no sean demasiado verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Log inicial
logger.info("=" * 80)
logger.info("=== INICIANDO BOT DE CAFE - MODO DIAGNÓSTICO ===")
logger.info("Python: %s", sys.version)
logger.info("Sistema operativo: %s", os.name)
logger.info("Directorio actual: %s", os.getcwd())
logger.info("=" * 80)

# Registrar información del entorno
try:
    import telegram
    logger.info("Versión de python-telegram-bot: %s", getattr(telegram, '__version__', 'Desconocida'))
    
    # Verificar si la versión de PTB es compatible
    version_str = getattr(telegram, '__version__', '0.0.0')
    version_parts = version_str.split('.')
    major_version = int(version_parts[0]) if version_parts and version_parts[0].isdigit() else 0
    
    if major_version < 20:
        logger.warning("ADVERTENCIA: Se recomienda usar python-telegram-bot v20.0 o superior. Versión actual: %s", version_str)
    else:
        logger.info("Versión de python-telegram-bot es compatible")
except ImportError:
    logger.critical("ERROR CRÍTICO: No se pudo importar el módulo telegram. Asegúrate de que python-telegram-bot esté instalado correctamente.")
    sys.exit(1)
except Exception as e:
    logger.error("Error al verificar versión de python-telegram-bot: %s", e)

# Importar configuración
logger.info("Importando módulo de configuración...")
try:
    from config import TOKEN, sheets_configured
    logger.info("Módulo de configuración importado correctamente")
    
    # Verificar TOKEN
    if not TOKEN:
        logger.critical("ERROR CRÍTICO: TOKEN no está configurado en el módulo config.py")
        sys.exit(1)
    else:
        logger.info("TOKEN configurado correctamente: %s...", TOKEN[:8] if TOKEN else "")
except ImportError:
    logger.critical("ERROR CRÍTICO: No se pudo importar el módulo config.py. Asegúrate de que existe.")
    sys.exit(1)
except Exception as e:
    logger.critical("ERROR CRÍTICO al importar configuración: %s", e)
    logger.critical(traceback.format_exc())
    sys.exit(1)

# Importar utilidades
logger.info("Importando módulo de utilidades...")
try:
    from utils.sheets import initialize_sheets
    logger.info("Módulo de utilidades importado correctamente")
except ImportError:
    logger.critical("ERROR CRÍTICO: No se pudo importar el módulo utils.sheets. Asegúrate de que existe.")
    sys.exit(1)
except Exception as e:
    logger.critical("ERROR CRÍTICO al importar utilidades: %s", e)
    logger.critical(traceback.format_exc())
    sys.exit(1)

# Función auxiliar para importar módulos con manejo detallado de errores
def import_module_safe(module_path, item_name=None):
    """Importa un módulo o un item específico de un módulo con manejo detallado de errores"""
    try:
        logger.debug("Intentando importar %s desde %s", item_name if item_name else "módulo", module_path)
        
        # Primero verificar si el módulo existe
        module_parts = module_path.split('.')
        base_module = module_parts[0]
        
        if not importlib.util.find_spec(base_module):
            logger.error("El módulo base '%s' no existe o no se puede encontrar", base_module)
            return None
        
        # Importar el módulo o item específico
        if item_name:
            module = importlib.import_module(module_path)
            if not hasattr(module, item_name):
                logger.error("El item '%s' no existe en el módulo '%s'", item_name, module_path)
                return None
            return getattr(module, item_name)
        else:
            return importlib.import_module(module_path)
    
    except ImportError as e:
        logger.error("Error de importación para %s: %s", module_path, e)
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error("Error al importar %s: %s", module_path, e)
        logger.error(traceback.format_exc())
        return None

# Intentar importar handlers con captura de errores
handlers_info = {}

logger.info("Importando handlers básicos...")
try:
    # Importar handlers básicos
    from handlers.start import start_command, help_command
    handlers_info["start"] = {"status": "OK", "details": "Importado correctamente"}
except Exception as e:
    logger.error("ERROR importando handlers básicos: %s", e)
    logger.error(traceback.format_exc())
    handlers_info["start"] = {"status": "ERROR", "details": str(e)}

# Lista de handlers principales a importar
handlers_to_import = [
    {"name": "compras", "module": "handlers.compras", "function": "register_compras_handlers"},
    {"name": "proceso", "module": "handlers.proceso", "function": "register_proceso_handlers"},
    {"name": "gastos", "module": "handlers.gastos", "function": "register_gastos_handlers"},
    {"name": "ventas", "module": "handlers.ventas", "function": "register_ventas_handlers"},
    {"name": "reportes", "module": "handlers.reportes", "function": "register_reportes_handlers"},
    {"name": "pedidos", "module": "handlers.pedidos", "function": "register_pedidos_handlers"},
    {"name": "adelantos", "module": "handlers.adelantos", "function": "register_adelantos_handlers"},
    {"name": "compra_adelanto", "module": "handlers.compra_adelanto", "function": "register_compra_adelanto_handlers"},
    {"name": "almacen", "module": "handlers.almacen", "function": "register_almacen_handlers"}
]

# Importar handlers principales
logger.info("Importando handlers principales...")
for handler_info in handlers_to_import:
    name = handler_info["name"]
    module = handler_info["module"]
    function = handler_info["function"]
    
    logger.info("Importando handler %s desde %s.%s", name, module, function)
    try:
        handler_func = import_module_safe(module, function)
        if handler_func:
            handlers_info[name] = {
                "status": "OK", 
                "details": "Importado correctamente",
                "function": handler_func
            }
            logger.info("Handler %s importado correctamente", name)
        else:
            handlers_info[name] = {
                "status": "ERROR", 
                "details": f"No se pudo importar {function} desde {module}",
                "function": None
            }
            logger.error("Error al importar handler %s", name)
    except Exception as e:
        logger.error("ERROR importando handler %s: %s", name, e)
        logger.error(traceback.format_exc())
        handlers_info[name] = {"status": "ERROR", "details": str(e), "function": None}

# Import especial para documents con captura de error detallada
logger.info("Importando módulo especial documents...")
try:
    logger.info("Verificando existencia del módulo documents...")
    if importlib.util.find_spec("handlers.documents"):
        logger.info("Módulo documents encontrado, intentando importar...")
        documents_module = import_module_safe("handlers.documents")
        
        if documents_module:
            logger.info("Módulo documents importado correctamente, verificando función register_documents_handlers...")
            if hasattr(documents_module, "register_documents_handlers"):
                register_documents_handlers = documents_module.register_documents_handlers
                logger.info("Función register_documents_handlers encontrada correctamente")
                handlers_info["documents"] = {
                    "status": "OK", 
                    "details": "Importado correctamente",
                    "function": register_documents_handlers
                }
            else:
                logger.error("La función register_documents_handlers no existe en el módulo documents")
                register_documents_handlers = None
                handlers_info["documents"] = {
                    "status": "ERROR", 
                    "details": "La función register_documents_handlers no existe en el módulo",
                    "function": None
                }
        else:
            logger.error("No se pudo importar el módulo documents")
            register_documents_handlers = None
            handlers_info["documents"] = {
                "status": "ERROR", 
                "details": "No se pudo importar el módulo",
                "function": None
            }
    else:
        logger.error("El módulo handlers.documents no existe o no se puede encontrar")
        register_documents_handlers = None
        handlers_info["documents"] = {
            "status": "ERROR", 
            "details": "El módulo no existe o no se puede encontrar",
            "function": None
        }
except Exception as e:
    logger.error("ERROR importando módulo documents: %s", e)
    logger.error(traceback.format_exc())
    register_documents_handlers = None
    handlers_info["documents"] = {"status": "ERROR", "details": str(e), "function": None}

# Verificar también la función documento_command para uso directo
try:
    logger.info("Intentando importar función documento_command directamente...")
    from handlers.documents import documento_command, cancelar
    logger.info("Función documento_command importada correctamente")
    handlers_info["documento_command"] = {"status": "OK", "details": "Importado correctamente"}
except Exception as e:
    logger.error("ERROR importando función documento_command: %s", e)
    logger.error(traceback.format_exc())
    documento_command = None
    cancelar = None
    handlers_info["documento_command"] = {"status": "ERROR", "details": str(e)}

# Import del módulo de diagnóstico
logger.info("Importando módulo diagnostico...")
try:
    diagnostico_module = import_module_safe("handlers.diagnostico")
    if diagnostico_module and hasattr(diagnostico_module, "register_diagnostico_handlers"):
        register_diagnostico_handlers = diagnostico_module.register_diagnostico_handlers
        logger.info("Módulo diagnostico importado correctamente")
        handlers_info["diagnostico"] = {
            "status": "OK", 
            "details": "Importado correctamente",
            "function": register_diagnostico_handlers
        }
    else:
        logger.error("No se pudo importar register_diagnostico_handlers")
        register_diagnostico_handlers = None
        handlers_info["diagnostico"] = {
            "status": "ERROR", 
            "details": "No se pudo importar la función register_diagnostico_handlers",
            "function": None
        }
except Exception as e:
    logger.error("ERROR importando módulo diagnostico: %s", e)
    logger.error(traceback.format_exc())
    register_diagnostico_handlers = None
    handlers_info["diagnostico"] = {"status": "ERROR", "details": str(e), "function": None}

# Crear un resumen del estado de las importaciones
logger.info("Resumen de importaciones:")
for name, info in handlers_info.items():
    status = info["status"]
    details = info["details"]
    logger.info("- %s: %s (%s)", name, status, details)

# Función para verificar el estado de los handlers
def get_handlers_status():
    """Genera un informe detallado del estado de los handlers"""
    ok_count = sum(1 for info in handlers_info.values() if info["status"] == "OK")
    error_count = sum(1 for info in handlers_info.values() if info["status"] == "ERROR")
    
    report = f"Estado de handlers: {ok_count} OK, {error_count} ERROR\n"
    
    # Verificar handlers críticos
    critical_handlers = ["documents", "documento_command"]
    critical_ok = all(handlers_info.get(h, {}).get("status") == "OK" for h in critical_handlers)
    
    if critical_ok:
        report += "Estado de handlers críticos: OK\n"
    else:
        report += "Estado de handlers críticos: ERROR\n"
        for handler in critical_handlers:
            status = handlers_info.get(handler, {}).get("status", "DESCONOCIDO")
            details = handlers_info.get(handler, {}).get("details", "Sin detalles")
            report += f"- {handler}: {status} ({details})\n"
    
    return report

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
    logger.info("Iniciando bot de Telegram para Gestión de Café - MODO DIAGNÓSTICO")
    
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
        logger.critical(f"ERROR CRÍTICO al crear aplicación: {e}")
        logger.critical(traceback.format_exc())
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
    
    # Registrar handlers específicos
    handlers_registrados = 0
    handlers_fallidos = 0
    
    # Registrar cada handler con manejo de excepciones individual
    for name, info in handlers_info.items():
        if name not in ["start", "documento_command", "documents", "diagnostico"]:  # Estos se manejan por separado
            handler_func = info.get("function")
            if handler_func:
                try:
                    logger.info(f"Registrando handler: {name}...")
                    handler_func(application)
                    logger.info(f"Handler {name} registrado correctamente")
                    handlers_registrados += 1
                except Exception as e:
                    logger.error(f"Error al registrar handler {name}: {e}")
                    logger.error(traceback.format_exc())
                    handlers_fallidos += 1
    
    # MÚLTIPLES INTENTOS PARA REGISTRAR EL HANDLER DE DOCUMENTOS
    documento_handler_registrado = False
    
    # Intento 1: Registrar el handler completo
    if register_documents_handlers:
        try:
            logger.info("INTENTO 1: Registrando handler completo documents...")
            register_documents_handlers(application)
            logger.info("Handler completo documents registrado correctamente")
            handlers_registrados += 1
            documento_handler_registrado = True
        except Exception as e:
            logger.error(f"Error al registrar handler completo documents: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    else:
        logger.error("No se puede intentar el registro completo documents: La función no está disponible")
    
    # Intento 2: Registrar comandos individuales si está disponible
    if not documento_handler_registrado and documento_command and cancelar:
        try:
            logger.info("INTENTO 2: Registrando comandos /documento y /cancelar directamente...")
            
            # Registrar el comando /documento directamente
            application.add_handler(CommandHandler("documento", documento_command))
            logger.info("Comando /documento registrado correctamente")
            
            # Registrar el comando /cancelar
            application.add_handler(CommandHandler("cancelar", cancelar))
            logger.info("Comando /cancelar registrado correctamente")
            
            # Crear un conversation handler básico para los estados
            try:
                logger.info("Creando ConversationHandler básico...")
                
                # Importar los estados de la conversación
                from handlers.documents import SELECCIONAR_TIPO, SELECCIONAR_ID, SUBIR_DOCUMENTO, CONFIRMAR
                from handlers.documents import seleccionar_tipo, seleccionar_id, subir_documento, confirmar
                
                # Crear manejador de conversación
                conv_handler = ConversationHandler(
                    entry_points=[],  # Vacío, ya registramos el comando directamente
                    states={
                        SELECCIONAR_TIPO: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_tipo)],
                        SELECCIONAR_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_id)],
                        SUBIR_DOCUMENTO: [MessageHandler(filters.PHOTO, subir_documento)],
                        CONFIRMAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirmar)],
                    },
                    fallbacks=[CommandHandler("cancelar", cancelar)],
                )
                
                # Agregar el manejador a la aplicación
                application.add_handler(conv_handler)
                logger.info("ConversationHandler básico registrado correctamente")
                
                handlers_registrados += 1
                documento_handler_registrado = True
            except Exception as e:
                logger.error(f"Error al crear ConversationHandler básico: {e}")
                logger.error(traceback.format_exc())
                # Continuamos porque ya registramos los comandos directamente
                documento_handler_registrado = True
        except Exception as e:
            logger.error(f"Error al registrar comandos individuales: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    else:
        if documento_handler_registrado:
            logger.info("No es necesario registrar comandos individuales: Ya se registró el handler completo")
        else:
            logger.error("No se puede intentar registrar comandos individuales: Las funciones no están disponibles")
    
    # Intento 3: Registrar un handler mínimo como último recurso
    if not documento_handler_registrado:
        try:
            logger.info("INTENTO 3: Registrando handler mínimo para /documento como último recurso...")
            
            # Función para manejar el comando /documento como último recurso
            async def documento_minimo(update, context):
                logger.info("Ejecutando handler mínimo para /documento")
                user = update.effective_user
                await update.message.reply_text(
                    f"⚠️ Hola, {user.mention_html()}!\n\n"
                    "El sistema de documentos está en mantenimiento.\n\n"
                    "Por favor, envía la evidencia de pago junto con los siguientes datos:\n"
                    "- Tipo: COMPRA o VENTA\n"
                    "- ID de la operación\n"
                    "- Descripción breve\n\n"
                    "Un administrador procesará tu solicitud manualmente.",
                    parse_mode="HTML"
                )
            
            # Registrar el comando /documento con el handler mínimo
            application.add_handler(CommandHandler("documento", documento_minimo))
            logger.info("Handler mínimo para /documento registrado correctamente")
            
            async def cancelar_minimo(update, context):
                logger.info("Ejecutando handler mínimo para /cancelar")
                await update.message.reply_text("Operación cancelada.")
            
            # Registrar el comando /cancelar con el handler mínimo
            application.add_handler(CommandHandler("cancelar", cancelar_minimo))
            logger.info("Handler mínimo para /cancelar registrado correctamente")
            
            handlers_registrados += 1
            documento_handler_registrado = True
        except Exception as e:
            logger.error(f"Error al registrar handler mínimo: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    
    # Registrar comando test_documento para diagnóstico
    try:
        logger.info("Registrando comando de diagnóstico /test_documento...")
        
        async def test_documento(update, context):
            """Comando de diagnóstico para verificar el handler de documentos"""
            logger.info("Comando /test_documento ejecutado por usuario %s", update.effective_user.id)
            
            # Generar informe del estado de los handlers
            report = get_handlers_status()
            
            await update.message.reply_text(
                "📋 DIAGNÓSTICO DEL HANDLER DE DOCUMENTOS\n\n"
                f"{report}\n\n"
                "Si el handler documents está marcado como ERROR, no podrás usar el comando /documento.\n\n"
                "Para más información, consulta los logs del servidor."
            )
        
        application.add_handler(CommandHandler("test_documento", test_documento))
        logger.info("Comando de diagnóstico /test_documento registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comando de diagnóstico /test_documento: {e}")
        logger.error(traceback.format_exc())
    
    # Registrar handler de diagnóstico (con verificación especial)
    if register_diagnostico_handlers:
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
    
    # Registrar comando de test adicional
    try:
        logger.info("Registrando comando de test general...")
        
        async def test_bot(update, context):
            await update.message.reply_text(
                "✅ El bot está funcionando correctamente y puede recibir comandos.\n\n"
                "Sistema de documentos: " + ("✅ ACTIVO" if documento_handler_registrado else "❌ INACTIVO") + "\n\n"
                "Usa /test_documento para más información sobre el sistema de documentos."
            )
        
        application.add_handler(CommandHandler("test_bot", test_bot))
        logger.info("Comando de test general registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comando de test general: {e}")
        logger.error(traceback.format_exc())
    
    # Registrar manejador para cualquier mensaje que mencione "documento" o "evidencia"
    try:
        logger.info("Registrando manejador para sugerencias de documento...")
        
        async def sugerir_documento(update, context):
            """Sugiere usar /test_documento cuando se mencionan palabras clave"""
            text = update.message.text.lower()
            if any(palabra in text for palabra in ["documento", "documentos", "evidencia", "comprobante", "pago"]):
                logger.info("Detectada palabra clave relacionada con documentos")
                await update.message.reply_text(
                    "💡 ¿Intentas subir un documento o evidencia de pago?\n\n"
                    "Usa /test_documento para verificar el estado del sistema de documentos."
                )
        
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                sugerir_documento
            )
        )
        logger.info("Manejador para sugerencias de documento registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar manejador para sugerencias: {e}")
        logger.error(traceback.format_exc())
    
    # Resumen de registro de handlers
    logger.info(f"Resumen de registro de handlers: {handlers_registrados} éxitos, {handlers_fallidos} fallos")
    logger.info(f"Estado del handler de documentos: {'REGISTRADO' if documento_handler_registrado else 'NO REGISTRADO'}")
    
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
        logger.critical(f"Error fatal en la ejecución del bot: {e}")
        logger.critical(traceback.format_exc())