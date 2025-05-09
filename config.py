import os
from dotenv import load_dotenv

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

# Asegurar que el directorio de datos existe (se mantiene para compatibilidad)
os.makedirs(DATA_DIR, exist_ok=True)

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
