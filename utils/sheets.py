import os
import json
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Configurar logging
logger = logging.getLogger(__name__)

# Hojas para cada tipo de dato
SHEET_IDS = {
    'compras': 0,  # Los ids son índices (0 para la primera hoja, 1 para la segunda, etc.)
    'proceso': 1,
    'gastos': 2,
    'ventas': 3
}

# Cabeceras para cada hoja
HEADERS = {
    'compras': ['fecha', 'tipo_cafe', 'proveedor', 'cantidad', 'precio', 'total'],
    'proceso': ['fecha', 'lote', 'estado', 'cantidad', 'notas'],
    'gastos': ['fecha', 'concepto', 'monto', 'categoria', 'notas'],
    'ventas': ['fecha', 'cliente', 'producto', 'cantidad', 'precio', 'total']
}

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

def initialize_sheets():
    """Inicializa las hojas de cálculo con las cabeceras si están vacías"""
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        # Verificar y configurar cada hoja
        for sheet_name, header in HEADERS.items():
            try:
                # Obtener datos actuales
                range_name = f"{sheet_name}!A1:Z1"
                result = sheets.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                
                # Si la hoja está vacía o no tiene cabeceras, agregarlas
                if not values:
                    logger.info(f"Inicializando hoja '{sheet_name}' con cabeceras: {header}")
                    sheets.values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption="RAW",
                        body={"values": [header]}
                    ).execute()
                    logger.info(f"Hoja '{sheet_name}' inicializada con cabeceras")
                else:
                    logger.info(f"Hoja '{sheet_name}' ya tiene datos: {values}")
            except Exception as e:
                logger.error(f"Error al inicializar la hoja '{sheet_name}': {e}")
                raise
                
    except Exception as e:
        logger.error(f"Error al inicializar las hojas: {e}")
        raise

def append_data(sheet_name, data):
    """Añade una fila de datos a la hoja especificada"""
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        # Convertir el diccionario a una lista ordenada según las cabeceras
        headers = HEADERS[sheet_name]
        row_data = [data.get(header, "") for header in headers]
        
        logger.info(f"Añadiendo datos a '{sheet_name}': {data}")
        logger.info(f"Datos formateados para Sheets: {row_data}")
        
        range_name = f"{sheet_name}!A:Z"
        result = sheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_data]}
        ).execute()
        
        logger.info(f"Datos añadidos correctamente a '{sheet_name}'. Respuesta: {result}")
        return True
    except Exception as e:
        logger.error(f"Error al añadir datos a {sheet_name}: {e}")
        return False

def update_cell(sheet_name, row_index, column_name, value):
    """Actualiza una celda específica en la hoja de cálculo.
    
    Args:
        sheet_name: Nombre de la hoja
        row_index: Índice de la fila (basado en 0 para las filas de datos, excluyendo las cabeceras)
        column_name: Nombre de la columna
        value: Nuevo valor para la celda
    
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        # Obtener índice de la columna
        headers = HEADERS[sheet_name]
        if column_name not in headers:
            logger.error(f"Nombre de columna inválido: {column_name}")
            raise ValueError(f"Nombre de columna inválido: {column_name}")
        
        column_index = headers.index(column_name)
        
        # Convertir índice de fila (desde 0) a número de fila real en la hoja (desde 1, contando cabeceras)
        # Fila 1 son las cabeceras, los datos comienzan en la fila 2
        real_row = row_index + 2
        
        # Convertir índice de columna a letra de columna de Excel (A, B, C, ...)
        column_letter = chr(65 + column_index)  # 65 es el código ASCII para 'A'
        cell_reference = f"{column_letter}{real_row}"
        
        logger.info(f"Actualizando celda {cell_reference} en hoja '{sheet_name}' con valor: {value}")
        
        # Actualizar celda
        result = sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!{cell_reference}",
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]}
        ).execute()
        
        logger.info(f"Celda actualizada correctamente. Respuesta: {result}")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar celda: {e}")
        return False

def get_all_data(sheet_name):
    """Obtiene todos los datos de la hoja especificada"""
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        range_name = f"{sheet_name}!A:Z"
        result = sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.info(f"No hay datos en la hoja '{sheet_name}'")
            return []
        
        # Convertir filas a diccionarios usando las cabeceras
        headers = values[0]
        rows = []
        
        for i, row in enumerate(values[1:]):  # Saltar la fila de cabeceras
            # Asegurarse de que la fila tenga la misma longitud que las cabeceras
            row_padded = row + [""] * (len(headers) - len(row))
            # Añadir el _row_index para referencia futura (basado en 0)
            row_dict = dict(zip(headers, row_padded))
            row_dict['_row_index'] = i
            rows.append(row_dict)
        
        logger.info(f"Obtenidos {len(rows)} registros de '{sheet_name}'")
        return rows
    except Exception as e:
        logger.error(f"Error al obtener datos de {sheet_name}: {e}")
        return []

def get_filtered_data(sheet_name, filters=None, days=None):
    """
    Obtiene datos filtrados de la hoja especificada
    
    Args:
        sheet_name: Nombre de la hoja
        filters: Diccionario de filtros campo:valor
        days: Si se proporciona, filtra por entradas en los últimos X días
    """
    all_data = get_all_data(sheet_name)
    
    if not all_data:
        return []
    
    filtered_data = all_data
    
    # Aplicar filtros
    if filters:
        filtered_data = [
            row for row in filtered_data
            if all(row.get(key) == value for key, value in filters.items())
        ]
    
    # Aplicar filtro de fecha (para futura implementación)
    if days:
        # TODO: Implementar filtrado por fecha
        pass
    
    logger.info(f"Filtrado: de {len(all_data)} registros a {len(filtered_data)} registros")
    return filtered_data