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

# Inicializar variables para los handlers
register_compras_handlers = None
register_proceso_handlers = None
register_gastos_handlers = None
register_ventas_handlers = None
register_reportes_handlers = None
register_pedidos_handlers = None
register_pedidos_whatsapp_handlers = None  # Handler para pedidos de WhatsApp
register_adelantos_handlers = None
register_compra_adelanto_handlers = None
register_compra_mixta_handlers = None  # Variable para el handler de compra mixta
register_almacen_handlers = None
register_evidencias_handlers = None
register_evidencias_list_handlers = None
register_documento_emergency_handlers = None
register_diagnostico_handlers = None
register_capitalizacion_handlers = None  # Nuevo handler para capitalización

# Intentar importar handlers con captura de errores
try:
    logger.info("Importando handlers...")
    
    # Importar handlers
    from handlers.start import start_command, help_command
    
    try:
        from handlers.compras import register_compras_handlers
        logger.info("Handler de compras importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de compras: {e}")
    
    try:
        from handlers.proceso import register_proceso_handlers
        logger.info("Handler de proceso importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de proceso: {e}")
    
    try:
        from handlers.gastos import register_gastos_handlers
        logger.info("Handler de gastos importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de gastos: {e}")
    
    try:
        from handlers.ventas import register_ventas_handlers
        logger.info("Handler de ventas importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de ventas: {e}")
    
    try:
        from handlers.reportes import register_reportes_handlers
        logger.info("Handler de reportes importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de reportes: {e}")
    
    try:
        from handlers.pedidos import register_pedidos_handlers
        logger.info("Handler de pedidos importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de pedidos: {e}")
    
    try:
        from handlers.pedidos_whatsapp import register_pedidos_whatsapp_handlers
        logger.info("Handler de pedidos WhatsApp importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de pedidos WhatsApp: {e}")
    
    try:
        from handlers.adelantos import register_adelantos_handlers
        logger.info("Handler de adelantos importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de adelantos: {e}")
    
    try:
        from handlers.compra_adelanto import register_compra_adelanto_handlers
        logger.info("Handler de compra_adelanto importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de compra_adelanto: {e}")
    
    # NUEVO: Importar la versión V2 completamente corregida de compra_mixta
    try:
        logger.info("Importando módulo de compra_mixta versión 2...")
        from handlers.compra_mixta_v2 import register_compra_mixta_handlers
        logger.info("Módulo compra_mixta v2 importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo de compra_mixta v2: {e}")
        logger.error(traceback.format_exc())
        
        # Intentar importar la versión original como respaldo
        try:
            logger.info("Intentando importar módulo compra_mixta original como respaldo...")
            from handlers.compra_mixta import register_compra_mixta_handlers
            logger.info("Módulo compra_mixta original importado como respaldo")
        except Exception as e2:
            logger.error(f"ERROR importando módulo compra_mixta original: {e2}")
            logger.error(traceback.format_exc())
    
    try:
        from handlers.almacen import register_almacen_handlers
        logger.info("Handler de almacen importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de almacen: {e}")
    
    try:
        from handlers.evidencias import register_evidencias_handlers
        logger.info("Handler de evidencias importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de evidencias: {e}")
        logger.error(traceback.format_exc())
        
    try:
        from handlers.evidencias_list import register_evidencias_list_handlers
        logger.info("Handler de listado de evidencias importado correctamente")
    except Exception as e:
        logger.error(f"Error al importar handler de listado de evidencias: {e}")
        logger.error(traceback.format_exc())
    
    # NUEVO: Importar el módulo de capitalización
    try:
        logger.info("Importando módulo de capitalización...")
        from handlers.capitalizacion import register_capitalizacion_handlers
        logger.info("Módulo de capitalización importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo de capitalización: {e}")
        logger.error(traceback.format_exc())
    
    # NUEVO: Importar el módulo de emergencia para documentos
    try:
        logger.info("Importando módulo de emergencia para documentos...")
        from handlers.documento_emergency import register_documento_emergency_handlers
        logger.info("Módulo de emergencia para documentos importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo de emergencia para documentos: {e}")
        logger.error(traceback.format_exc())
    
    # Import del módulo de diagnóstico
    try:
        logger.info("Importando módulo diagnostico...")
        from handlers.diagnostico import register_diagnostico_handlers
        logger.info("Módulo diagnostico importado correctamente")
    except Exception as e:
        logger.error(f"ERROR importando módulo diagnostico: {e}")
        logger.error(traceback.format_exc())
    
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

def verificar_y_configurar_google_drive():
    """Verifica la configuración de Google Drive y configura las carpetas necesarias"""
    from config import DRIVE_ENABLED, DRIVE_EVIDENCIAS_ROOT_ID, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID
    
    if not DRIVE_ENABLED:
        logger.info("Google Drive está deshabilitado. No se iniciará la integración con Drive.")
        return False
    
    logger.info("Google Drive está habilitado, verificando configuración...")
    
    # Verificar si las credenciales de Google están disponibles
    from config import GOOGLE_CREDENTIALS
    if not GOOGLE_CREDENTIALS:
        logger.error("No se encontraron credenciales de Google. Google Drive no funcionará correctamente.")
        return False
    
    try:
        # Verificar si tenemos los IDs de las carpetas
        if not (DRIVE_EVIDENCIAS_ROOT_ID and DRIVE_EVIDENCIAS_COMPRAS_ID and DRIVE_EVIDENCIAS_VENTAS_ID):
            logger.warning("No se encontraron todos los IDs de carpetas de Google Drive necesarios.")
            logger.info("Configurando estructura de carpetas en Google Drive...")
            
            # Importar función para configurar carpetas
            from utils.drive import setup_drive_folders
            
            # Intentar configurar las carpetas
            result = setup_drive_folders()
            
            if result:
                logger.info("✅ Estructura de carpetas en Google Drive configurada exitosamente")
                
                # Verificar que los IDs se hayan actualizado correctamente
                from config import DRIVE_EVIDENCIAS_ROOT_ID, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID
                logger.info(f"ID carpeta raíz: {DRIVE_EVIDENCIAS_ROOT_ID}")
                logger.info(f"ID carpeta compras: {DRIVE_EVIDENCIAS_COMPRAS_ID}")
                logger.info(f"ID carpeta ventas: {DRIVE_EVIDENCIAS_VENTAS_ID}")
                
                return True
            else:
                logger.error("❌ No se pudo configurar la estructura de carpetas en Google Drive")
                return False
        else:
            # Si ya tenemos los IDs, verificar que sean válidos
            logger.info("IDs de carpetas de Google Drive encontrados. Verificando conexión...")
            
            # Importar función para probar la conexión
            from utils.drive import get_drive_service
            
            # Intentar obtener el servicio de Drive
            service = get_drive_service()
            
            if service:
                logger.info("✅ Conexión con Google Drive establecida correctamente")
                logger.info(f"ID carpeta raíz: {DRIVE_EVIDENCIAS_ROOT_ID}")
                logger.info(f"ID carpeta compras: {DRIVE_EVIDENCIAS_COMPRAS_ID}")
                logger.info(f"ID carpeta ventas: {DRIVE_EVIDENCIAS_VENTAS_ID}")
                return True
            else:
                logger.error("❌ No se pudo establecer conexión con Google Drive")
                return False
    
    except Exception as e:
        logger.error(f"Error al configurar Google Drive: {e}")
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
    
    # Inicializar la configuración de Google Drive
    drive_ok = verificar_y_configurar_google_drive()
    if not drive_ok:
        logger.warning("⚠️ Google Drive no está correctamente configurado. Las evidencias se guardarán localmente.")
    else:
        logger.info("✅ Google Drive configurado correctamente para el almacenamiento de evidencias.")
    
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
    
    # Lista de funciones de registro de handlers disponibles
    handler_functions = []
    
    # Añadir solo handlers que se han importado correctamente
    if register_compras_handlers:
        handler_functions.append(("compras", register_compras_handlers))
    if register_proceso_handlers:
        handler_functions.append(("proceso", register_proceso_handlers))
    if register_gastos_handlers:
        handler_functions.append(("gastos", register_gastos_handlers))
    if register_ventas_handlers:
        handler_functions.append(("ventas", register_ventas_handlers))
    if register_reportes_handlers:
        handler_functions.append(("reportes", register_reportes_handlers))
    if register_pedidos_handlers:
        handler_functions.append(("pedidos", register_pedidos_handlers))
    if register_pedidos_whatsapp_handlers:
        handler_functions.append(("pedidos_whatsapp", register_pedidos_whatsapp_handlers))
    if register_adelantos_handlers:
        handler_functions.append(("adelantos", register_adelantos_handlers))
    if register_compra_adelanto_handlers:
        handler_functions.append(("compra_adelanto", register_compra_adelanto_handlers))
    if register_compra_mixta_handlers:  # Handler para compra mixta
        handler_functions.append(("compra_mixta", register_compra_mixta_handlers))
    if register_almacen_handlers:
        handler_functions.append(("almacen", register_almacen_handlers))
    if register_evidencias_handlers:
        handler_functions.append(("evidencias", register_evidencias_handlers))
    if register_evidencias_list_handlers:
        handler_functions.append(("evidencias_list", register_evidencias_list_handlers))
    if register_capitalizacion_handlers:  # Handler para capitalización
        handler_functions.append(("capitalizacion", register_capitalizacion_handlers))
    
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
        logger.warning("No se pudo registrar el handler de diagnóstico: Módulo no disponible")
        handlers_fallidos += 1
    
    # Registrar comando de drive_status
    try:
        logger.info("Registrando comando de estado de Google Drive...")
        
        async def drive_status(update, context):
            from config import DRIVE_ENABLED, DRIVE_EVIDENCIAS_ROOT_ID, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID
            
            if DRIVE_ENABLED:
                await update.message.reply_text(
                    "📊 *ESTADO DE GOOGLE DRIVE*\n\n"
                    f"Estado: {'✅ ACTIVO' if drive_ok else '⚠️ CONFIGURADO PERO CON ERRORES'}\n"
                    f"Carpeta Raíz: {DRIVE_EVIDENCIAS_ROOT_ID[:10]}... (ID)\n"
                    f"Carpeta Compras: {DRIVE_EVIDENCIAS_COMPRAS_ID[:10]}... (ID)\n"
                    f"Carpeta Ventas: {DRIVE_EVIDENCIAS_VENTAS_ID[:10]}... (ID)\n\n"
                    "Si tienes problemas al subir evidencias, contacta al administrador.",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    "📊 *ESTADO DE GOOGLE DRIVE*\n\n"
                    "Estado: ❌ DESACTIVADO\n\n"
                    "La integración con Google Drive está desactivada. "
                    "Las evidencias se guardarán solo localmente.",
                    parse_mode="Markdown"
                )
        
        application.add_handler(CommandHandler("drive_status", drive_status))
        logger.info("Comando de estado de Google Drive registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comando de estado de Google Drive: {e}")
        logger.error(traceback.format_exc())
    
    # Registrar comando de test directo (sin usar el módulo documents)
    try:
        logger.info("Registrando comando de test directo...")
        application.add_handler(
            CommandHandler("test_bot", 
                lambda update, context: update.message.reply_text(
                    "\ud83d\udc4d El bot está funcionando correctamente y puede recibir comandos.\n\n"
                    f"Sistema de documentos: {'ACTIVO (modo emergencia)' if documento_handler_registrado else 'INACTIVO'}\n"
                    f"Google Drive: {'ACTIVO' if drive_ok else 'INACTIVO'}\n\n"
                    "Usa /documento_status para más información sobre el sistema de documentos.\n"
                    "Usa /drive_status para información sobre Google Drive."
                )
            )
        )
        logger.info("Comando de test directo registrado correctamente")
    except Exception as e:
        logger.error(f"Error al registrar comando de test directo: {e}")
        logger.error(traceback.format_exc())
    
    # Registrar comando de evidencia mínimo si el handler normal falló
    if "evidencias" not in [name for name, _ in handler_functions]:
        try:
            logger.info("Implementando handler mínimo para /evidencia como último recurso...")
            
            async def evidencia_minimo(update, context):
                await update.message.reply_text(
                    "⚠️ El sistema de evidencias está en mantenimiento.\n\n"
                    "Por favor, envía tu evidencia de pago como una foto normal, "
                    "e incluye en la descripción:\n"
                    "- Tipo: COMPRA o VENTA\n"
                    "- ID de la operación\n\n"
                    "Un administrador procesará tu evidencia manualmente."
                )
            
            application.add_handler(CommandHandler("evidencia", evidencia_minimo))
            logger.info("Handler mínimo para /evidencia implementado correctamente")
            handlers_registrados += 1
        except Exception as e:
            logger.error(f"Error al implementar handler mínimo para /evidencia: {e}")
            logger.error(traceback.format_exc())
            handlers_fallidos += 1
    
    # Resumen de registro de handlers
    logger.info(f"Resumen de registro de handlers: {handlers_registrados} éxitos, {handlers_fallidos} fallos")
    logger.info(f"Estado del handler de documentos: {'REGISTRADO' if documento_handler_registrado else 'NO REGISTRADO'}")
    logger.info(f"Estado de Google Drive: {'ACTIVO' if drive_ok else 'INACTIVO'}")
    
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