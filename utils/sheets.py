import os
import json
import logging
import uuid
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Configurar logging
logger = logging.getLogger(__name__)

# Hojas para cada tipo de dato
SHEET_IDS = {
    'compras': 0,  # Los ids son índices (0 para la primera hoja, 1 para la segunda, etc.)
    'proceso': 1,
    'gastos': 2,
    'ventas': 3,
    'adelantos': 4,  # Añadimos la hoja de adelantos con índice 4
    'almacen': 5     # Nueva hoja para el almacén centralizado
}

# Cabeceras para cada hoja - Añadimos fase_actual a compras e id único
HEADERS = {
    'compras': ['id', 'fecha', 'tipo_cafe', 'proveedor', 'cantidad', 'precio', 'total', 'fase_actual', 'kg_disponibles'],
    'proceso': ['fecha', 'origen', 'destino', 'cantidad', 'compras_ids', 'merma', 'notas', 'registrado_por'],
    'gastos': ['fecha', 'concepto', 'monto', 'categoria', 'notas'],
    'ventas': ['fecha', 'cliente', 'producto', 'cantidad', 'precio', 'total'],
    'adelantos': ['fecha', 'hora', 'proveedor', 'monto', 'saldo_restante', 'notas', 'registrado_por'],
    'almacen': ['fase', 'cantidad', 'ultima_actualizacion', 'notas']  # Nueva estructura para el almacén
}

# Definir las fases posibles del café
FASES_CAFE = ["CEREZO", "MOTE", "PERGAMINO", "VERDE", "TOSTADO", "MOLIDO"]

# Definir las transiciones permitidas entre fases - Actualizado para permitir PERGAMINO -> TOSTADO
TRANSICIONES_PERMITIDAS = {
    "CEREZO": ["MOTE", "PERGAMINO"],
    "MOTE": ["PERGAMINO"],
    "PERGAMINO": ["VERDE", "TOSTADO"],  # Ahora PERGAMINO puede ir a VERDE o directamente a TOSTADO
    "VERDE": ["TOSTADO"],
    "TOSTADO": ["MOLIDO"]
}

def generate_unique_id():
    """Genera un ID único para registros"""
    return str(uuid.uuid4().hex)[:8]  # Usar solo los primeros 8 caracteres para un ID más corto y legible

def get_credentials():
    """Obtiene credenciales para la API de Google Sheets desde variables de entorno"""
    # En producción, guarda estas credenciales como variable de entorno
    creds_json = os.getenv('GOOGLE_CREDENTIALS')
    
    if not creds_json:
        logger.error("Las credenciales de Google no están configuradas. Establece la variable de entorno GOOGLE_CREDENTIALS.")
        raise ValueError("Las credenciales de Google no están configuradas. Establece la variable de entorno GOOGLE_CREDENTIALS.")
    
    try:
        # Parsear JSON de credenciales desde la variable de entorno
        creds_info = json.loads(creds_json)
        
        # Crear credenciales desde la información JSON
        creds = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        return creds
    except json.JSONDecodeError as e:
        logger.error(f"Error al decodificar las credenciales JSON: {e}")
        raise ValueError(f"Las credenciales de Google no son un JSON válido: {e}")
    except Exception as e:
        logger.error(f"Error al obtener credenciales: {e}")
        raise

def get_sheet_service():
    """Crea y devuelve un servicio de Google Sheets API"""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)
    return service.spreadsheets()

def get_or_create_sheet():
    """Obtiene o crea una nueva hoja de cálculo para el bot"""
    # ID de la hoja de cálculo (debes crear una hoja y obtener su ID)
    spreadsheet_id = os.getenv('SPREADSHEET_ID')
    
    if not spreadsheet_id:
        logger.error("El ID de la hoja de cálculo no está configurado. Establece la variable de entorno SPREADSHEET_ID.")
        raise ValueError("El ID de la hoja de cálculo no está configurado. Establece la variable de entorno SPREADSHEET_ID.")
    
    logger.info(f"Usando hoja de cálculo con ID: {spreadsheet_id}")
    return spreadsheet_id