import os
import logging
from dotenv import load_dotenv
import pathlib

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

# Inicializar Google Sheets cuando se importa este módulo
sheets_configured = check_sheets_config()

# Configurar logging para este módulo
logger = logging.getLogger(__name__)

# Registro de configuración para diagnóstico
logger.info("=== CONFIGURACIÓN CARGADA ===")
logger.info(f"DRIVE_ENABLED: {DRIVE_ENABLED}")
logger.info(f"DRIVE_EVIDENCIAS_ROOT_ID: {DRIVE_EVIDENCIAS_ROOT_ID[:10] + '...' if DRIVE_EVIDENCIAS_ROOT_ID else 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_COMPRAS_ID: {DRIVE_EVIDENCIAS_COMPRAS_ID[:10] + '...' if DRIVE_EVIDENCIAS_COMPRAS_ID else 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_VENTAS_ID: {DRIVE_EVIDENCIAS_VENTAS_ID[:10] + '...' if DRIVE_EVIDENCIAS_VENTAS_ID else 'No configurado'}")
logger.info(f"SPREADSHEET_ID: {SPREADSHEET_ID[:10] + '...' if SPREADSHEET_ID else 'No configurado'}")
logger.info(f"GOOGLE_CREDENTIALS: {'Configurado' if GOOGLE_CREDENTIALS else 'No configurado'}")
logger.info(f"UPLOADS_FOLDER: {UPLOADS_FOLDER}")
logger.info("=== FIN DE CONFIGURACIÓN ===")

# Función para actualizar las variables de entorno en ejecución
# (útil cuando se configuran automáticamente las carpetas de Drive)
def update_env_var(name, value):
    """Actualiza una variable de entorno en tiempo de ejecución"""
    os.environ[name] = value
    globals()[name] = value
    logger.info(f"Variable de entorno actualizada: {name}={value[:10] + '...' if value and len(value) > 10 else value}")
    return True