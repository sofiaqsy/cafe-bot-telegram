import os
import logging
import traceback
import requests
from telegram.ext import Application, CommandHandler

# Configuración de logging avanzada
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO  # Cambiado a INFO para reducir verbosidad
)
logger = logging.getLogger(__name__)

# Asegurarse de que los logs de las bibliotecas no sean demasiado verbosos
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

# Importar configuración
logger.info("Importando configuración...")
from config import TOKEN, sheets_configured
from utils.sheets import initialize_sheets

# Log inicial
logger.info("=== INICIANDO BOT DE CAFE - MODO EMERGENCIA ===")

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
    
    # NUEVO: Importar el módulo de emergencia para documentos
    try:
        logger.info("Importando módulo de emergencia para documentos...")
        from handlers.documento_emergency import register_documento_emergency_handlers
        logger.info("Módulo de emergencia para documentos importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo de emergencia para documentos: {e}")
        logger.error(traceback.format_exc())
        register_documento_emergency_handlers = None
    
    # Intentar importar el módulo original de documents (para diagnóstico)
    try:
        logger.info("Intentando importar módulo documents original (solo para diagnóstico)...")
        from handlers.documents import register_documents_handlers
        logger.info("Módulo documents original importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo documents original: {e}")
        logger.error(traceback.format_exc())
        register_documents_handlers = None
    
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
    logger.info("Iniciando bot de Telegram para Gestión de Café en Heroku")
    logger.info(f"Token encontrado (primeros 5 caracteres): {TOKEN[:5]}...")
    
    # Eliminar webhook existente primero
    eliminar_webhook()
    
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
    
    # PRIORIDAD ALTA: Registrar el handler de emergencia para documentos
    documento_handler_registrado = False
    
    # Intentar registrar el handler de emergencia para documentos
    if register_documento_emergency_handlers:
        try:
            logger.info("PRIORIDAD ALTA: Registrando handler de emergencia para documentos...")
            register_documento_emergency_handlers(application)
            logger.info("Handler de emergencia para documentos registrado correctamente")
            documento_handler_registrado = True
            handlers_registrados += 1
        except Exception as e:
            logger.error(f"ERROR al registrar handler de emergencia para documentos: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    
    # Solo intentar registrar el handler original si el de emergencia no funcionó
    if not documento_handler_registrado and register_documents_handlers:
        try:
            logger.info("Intentando registrar handler de documentos original...")
            register_documents_handlers(application)
            logger.info("Handler de documentos original registrado correctamente")
            documento_handler_registrado = True
            handlers_registrados += 1
        except Exception as e:
            logger.error(f"Error al registrar handler de documentos original: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    
    # Si todavía no se ha registrado ningún handler para /documento, implementar una solución mínima
    if not documento_handler_registrado:
        try:
            logger.info("Implementando handler mínimo para /documento como último recurso...")
            
            async def documento_minimo(update, context):
                await update.message.reply_text(
                    "⚠️ El sistema de documentos está en mantenimiento.\n\n"
                    "Por favor, envía tu evidencia de pago como una foto normal, "
                    "e incluye en la descripción:\n"
                    "- Tipo: COMPRA o VENTA\n"
                    "- ID de la operación\n\n"
                    "Un administrador procesará tu evidencia manualmente."
                )
            
            application.add_handler(CommandHandler("documento", documento_minimo))
            logger.info("Handler mínimo para /documento implementado correctamente")
            documento_handler_registrado = True
            handlers_registrados += 1
        except Exception as e:
            logger.error(f"Error al implementar handler mínimo para /documento: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    
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
    
    # Registrar comando de test directo (sin usar el módulo documents)
    try:
        logger.info("Registrando comando de test directo...")
        application.add_handler(
            CommandHandler("test_bot", 
                lambda update, context: update.message.reply_text(
                    "\ud83d\udc4d El bot está funcionando correctamente y puede recibir comandos.\n\n"
                    f"Sistema de documentos: {'ACTIVO (modo emergencia)' if documento_handler_registrado else 'INACTIVO'}\n\n"
                    "Usa /documento_status para más información sobre el sistema de documentos."
                )
            )
        )
        logger.info("Comando de test directo registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comando de test directo: {e}")
        logger.error(traceback.format_exc())
    
    # Resumen de registro de handlers
    logger.info(f"Resumen de registro de handlers: {handlers_registrados} éxitos, {handlers_fallidos} fallos")
    logger.info(f"Estado del handler de documentos: {'REGISTRADO' if documento_handler_registrado else 'NO REGISTRADO'}")
    
    # Si todos los handlers fallaron, salir
    if handlers_registrados == 0 and handlers_fallidos > 0:
        logger.error("No se pudo registrar ningún handler. Finalizando inicialización.")
        return
    
    # Iniciar el bot
    try:
        logger.info("Bot iniciado en modo POLLING. Esperando comandos...")
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