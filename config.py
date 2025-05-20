import os
import logging
from dotenv import load_dotenv
import pathlib

# Configurar logging para config
logger = logging.getLogger(__name__)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Obtener el token del bot desde las variables de entorno
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Configuración de archivos de datos (se mantiene para compatibilidad)
DATA_DIR = "data"
COMPRAS_FILE = os.path.join(DATA_DIR, "compras.csv")
PROCESO_FILE = os.path.join(DATA_DIR, "proceso.csv")
GASTOS_FILE = os.path.join(DATA_DIR, "gastos.csv")
VENTAS_FILE = os.path.join(DATA_DIR, "ventas.csv")

# Configuración de Google Sheets
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")

# Configuración de Google Drive para almacenamiento de evidencias
DRIVE_ENABLED = os.getenv("DRIVE_ENABLED", "False").lower() in ("true", "1", "t")
DRIVE_EVIDENCIAS_ROOT_ID = os.getenv("DRIVE_EVIDENCIAS_ROOT_ID", "")
DRIVE_EVIDENCIAS_COMPRAS_ID = os.getenv("DRIVE_EVIDENCIAS_COMPRAS_ID", "")
DRIVE_EVIDENCIAS_VENTAS_ID = os.getenv("DRIVE_EVIDENCIAS_VENTAS_ID", "")

# Mostrar información sobre la configuración de Google Drive
logger.info(f"=== CONFIGURACIÓN DE GOOGLE DRIVE ===")
logger.info(f"DRIVE_ENABLED: {DRIVE_ENABLED}")
logger.info(f"DRIVE_EVIDENCIAS_ROOT_ID: {DRIVE_EVIDENCIAS_ROOT_ID}")
logger.info(f"DRIVE_EVIDENCIAS_COMPRAS_ID: {DRIVE_EVIDENCIAS_COMPRAS_ID}")
logger.info(f"DRIVE_EVIDENCIAS_VENTAS_ID: {DRIVE_EVIDENCIAS_VENTAS_ID}")

# Asegurar que el directorio de datos existe (se mantiene para compatibilidad)
os.makedirs(DATA_DIR, exist_ok=True)

# Configuración de carpeta para uploads de documentos
UPLOADS_FOLDER = os.path.join(pathlib.Path(__file__).parent.absolute(), "uploads")
os.makedirs(UPLOADS_FOLDER, exist_ok=True)

# Verificar configuración de Google Sheets
def check_sheets_config():
    """Verifica que la configuración de Google Sheets esté completa"""
    if not SPREADSHEET_ID:
        print("ADVERTENCIA: No se ha configurado SPREADSHEET_ID en las variables de entorno")
        return False
    
    if not GOOGLE_CREDENTIALS:
        print("ADVERTENCIA: No se ha configurado GOOGLE_CREDENTIALS en las variables de entorno")
        return False
    
    return True

# Verificar configuración de Google Drive
def check_drive_config():
    """Verifica que la configuración de Google Drive esté completa"""
    if not DRIVE_ENABLED:
        logger.warning("Google Drive no está habilitado (DRIVE_ENABLED=False)")
        return False
    
    if not GOOGLE_CREDENTIALS:
        logger.error("GOOGLE_CREDENTIALS no está configurado, se requiere para Google Drive")
        return False
    
    # Verificar las carpetas de Google Drive
    missing_folders = []
    if not DRIVE_EVIDENCIAS_ROOT_ID:
        missing_folders.append("DRIVE_EVIDENCIAS_ROOT_ID")
    if not DRIVE_EVIDENCIAS_COMPRAS_ID:
        missing_folders.append("DRIVE_EVIDENCIAS_COMPRAS_ID")
    if not DRIVE_EVIDENCIAS_VENTAS_ID:
        missing_folders.append("DRIVE_EVIDENCIAS_VENTAS_ID")
    
    if missing_folders:
        logger.warning(f"Faltan configurar las siguientes carpetas de Google Drive: {', '.join(missing_folders)}")
        return False
    
    logger.info("La configuración de Google Drive está completa")
    return True

# Inicializar Google Sheets cuando se importa este módulo
sheets_configured = check_sheets_config()
drive_configured = check_drive_config()
