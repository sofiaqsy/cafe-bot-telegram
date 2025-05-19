"""
Módulo para gestionar la conexión con el servicio de Google Sheets.
"""
import json
import logging
from typing import Any
import googleapiclient.discovery
from google.oauth2 import service_account
from config import SPREADSHEET_ID, GOOGLE_CREDENTIALS

# Configurar logging
logger = logging.getLogger(__name__)

# Variables globales para el servicio de Google Sheets
_sheet_service = None
# Variable para controlar la inicialización
_sheets_initialized = False

def get_sheet_service():
    """
    Obtiene el servicio de Google Sheets, creándolo si es necesario.
    
    Returns:
        El servicio de Google Sheets
    """
    global _sheet_service
    
    if _sheet_service is None:
        try:
            # Si GOOGLE_CREDENTIALS es un string JSON, cargarlo como un dict
            if GOOGLE_CREDENTIALS.startswith('{'):
                credentials_info = json.loads(GOOGLE_CREDENTIALS)
            else:
                # Si es un path a un archivo, cargarlo
                with open(GOOGLE_CREDENTIALS, 'r') as f:
                    credentials_info = json.load(f)
            
            # Crear credenciales a partir de la información
            credentials = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Crear servicio
            _sheet_service = googleapiclient.discovery.build('sheets', 'v4', credentials=credentials)
            logger.info("Servicio de Google Sheets inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar el servicio de Google Sheets: {e}")
            raise
    
    return _sheet_service

def get_or_create_sheet():
    """
    Obtiene el ID de la hoja, verificando que exista y creándola si es necesario.
    
    Returns:
        str: ID de la hoja de cálculo
    """
    # Por ahora, simplemente devolver el ID configurado
    return SPREADSHEET_ID

def get_sheets_initialized():
    """
    Devuelve si las hojas ya han sido inicializadas en esta sesión.
    
    Returns:
        bool: True si las hojas ya han sido inicializadas, False en caso contrario
    """
    global _sheets_initialized
    return _sheets_initialized

def set_sheets_initialized(value: bool):
    """
    Establece el estado de inicialización de las hojas.
    
    Args:
        value: True si las hojas están inicializadas, False en caso contrario
    """
    global _sheets_initialized
    _sheets_initialized = value

def get_sheet_id(sheet_name: str) -> Any:
    """
    Obtiene el ID interno de una hoja específica dentro del spreadsheet.
    
    Args:
        sheet_name: Nombre de la hoja
        
    Returns:
        Any: ID interno de la hoja o None si no se encuentra
    """
    try:
        sheets = get_sheet_service()
        spreadsheet_id = get_or_create_sheet()
        
        # Obtener metadatos de todas las hojas
        sheet_metadata = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets_list = sheet_metadata.get('sheets', [])
        
        # Buscar la hoja específica por nombre
        for sheet in sheets_list:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        
        logger.warning(f"No se encontró la hoja '{sheet_name}' en el spreadsheet")
        return None
    except Exception as e:
        logger.error(f"Error al obtener ID de la hoja '{sheet_name}': {e}")
        return None