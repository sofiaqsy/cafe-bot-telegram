import os
import logging
import datetime
import string
import random
import json
from typing import Dict, List, Any, Optional, Union
import googleapiclient.discovery
from google.oauth2 import service_account
from config import SPREADSHEET_ID, GOOGLE_CREDENTIALS

# Configurar logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Definir constantes
FASES_CAFE = ["CEREZO", "MOTE", "PERGAMINO", "VERDE", "TOSTADO", "MOLIDO"]

# Definir transiciones válidas entre fases
TRANSICIONES_PERMITIDAS = {
    "CEREZO": ["MOTE", "PERGAMINO"],  # Actualizado para permitir CEREZO a PERGAMINO
    "MOTE": ["PERGAMINO"],
    "PERGAMINO": ["VERDE", "TOSTADO", "MOLIDO"],
    "VERDE": ["TOSTADO"],
    "TOSTADO": ["MOLIDO"],
    "MOLIDO": []
}

# Porcentajes aproximados de merma por tipo de transición
MERMAS_SUGERIDAS = {
    "CEREZO_MOTE": 0.85,      # 85% de pérdida de peso cerezo a mote
    "CEREZO_PERGAMINO": 0.88, # 88% de pérdida de cerezo a pergamino (agregado)
    "MOTE_PERGAMINO": 0.20,   # 20% de pérdida de mote a pergamino
    "PERGAMINO_VERDE": 0.18,  # 18% de pérdida de pergamino a verde
    "PERGAMINO_TOSTADO": 0.20, # 20% de pérdida de pergamino a tostado
    "PERGAMINO_MOLIDO": 0.25, # 25% de pérdida de pergamino a molido
    "VERDE_TOSTADO": 0.15,    # 15% de pérdida de verde a tostado
    "TOSTADO_MOLIDO": 0.05    # 5% de pérdida de tostado a molido
}

# Cabeceras para las hojas
HEADERS = {
    "compras": ["id", "fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "preciototal", "registrado_por", "notas"],
    "proceso": ["fecha", "origen", "destino", "cantidad", "compras_ids", "merma", "merma_estimada", "cantidad_resultante_esperada", "cantidad_resultante", "notas", "registrado_por"],
    "gastos": ["fecha", "categoria", "monto", "descripcion", "registrado_por"],
    "ventas": ["fecha", "cliente", "tipo_cafe", "peso", "precio_kg", "total", "almacen_id", "notas", "registrado_por"],
    "pedidos": ["fecha", "cliente", "tipo_cafe", "cantidad", "precio_kg", "total", "estado", "fecha_entrega", "notas", "registrado_por"],
    "adelantos": ["fecha", "hora", "cliente", "monto", "notas", "registrado_por"],
    "almacen": ["id", "compra_id", "tipo_cafe_origen", "fecha", "cantidad", "fase_actual", "cantidad_actual", "notas", "fecha_actualizacion"]
}

# Variables globales para el servicio de Google Sheets
_sheet_service = None
# Variable para controlar la inicialización
_sheets_initialized = False

def get_sheet_service():
    """Obtiene el servicio de Google Sheets, creándolo si es necesario"""
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
    """Obtiene el ID de la hoja, verificando que exista y creándola si es necesario"""
    # Por ahora, simplemente devolver el ID configurado
    return SPREADSHEET_ID