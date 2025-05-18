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
    'ventas': 3,
    'adelantos': 4  # Añadimos la hoja de adelantos con índice 4
}

# Cabeceras para cada hoja - Añadimos fase_actual a compras
HEADERS = {
    'compras': ['fecha', 'tipo_cafe', 'proveedor', 'cantidad', 'precio', 'total', 'fase_actual', 'kg_disponibles'],
    'proceso': ['fecha', 'origen', 'destino', 'cantidad', 'compras_ids', 'merma', 'notas', 'registrado_por'],
    'gastos': ['fecha', 'concepto', 'monto', 'categoria', 'notas'],
    'ventas': ['fecha', 'cliente', 'producto', 'cantidad', 'precio', 'total'],
    'adelantos': ['fecha', 'hora', 'proveedor', 'monto', 'saldo_restante', 'notas', 'registrado_por']
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
                    # Verificar si las cabeceras existentes coinciden con las esperadas
                    logger.info(f"Cabeceras existentes en hoja '{sheet_name}': {values[0]}")
                    logger.info(f"Cabeceras esperadas: {header}")
                    
                    # Para compras, añadir columnas fase_actual y kg_disponibles si no existen
                    if sheet_name == 'compras' and len(values[0]) < len(header):
                        # Si hay que actualizar las cabeceras
                        logger.warning(f"Actualizando cabeceras de '{sheet_name}' para incluir nuevos campos")
                        
                        # Actualizar cabeceras
                        sheets.values().update(
                            spreadsheetId=spreadsheet_id,
                            range=range_name,
                            valueInputOption="RAW",
                            body={"values": [header]}
                        ).execute()
                        
                        # Inicializar nuevas columnas para filas existentes
                        data_range_name = f"{sheet_name}!A2:Z"
                        existing_data = sheets.values().get(
                            spreadsheetId=spreadsheet_id,
                            range=data_range_name
                        ).execute()
                        
                        existing_rows = existing_data.get('values', [])
                        if existing_rows:
                            # Para cada fila existente, actualizar fase_actual con tipo_cafe
                            for i, row in enumerate(existing_rows):
                                row_num = i + 2  # +2 porque empezamos en la fila 2 (después de las cabeceras)
                                
                                # Si la fila tiene al menos el campo tipo_cafe (índice 1)
                                if len(row) > 1 and row[1]:
                                    tipo_cafe = row[1]
                                    
                                    # Si no existe fase_actual o está vacía
                                    if len(row) <= 6 or not row[6]:  # 6 sería el índice de fase_actual
                                        # Actualizar fase_actual = tipo_cafe
                                        sheets.values().update(
                                            spreadsheetId=spreadsheet_id,
                                            range=f"{sheet_name}!G{row_num}",  # G es fase_actual (columna 7)
                                            valueInputOption="RAW",
                                            body={"values": [[tipo_cafe]]}
                                        ).execute()
                                        logger.info(f"Actualizada fase_actual en fila {row_num}")
                                    
                                    # Si no existe kg_disponibles o está vacía
                                    if len(row) <= 7 or not row[7]:  # 7 sería el índice de kg_disponibles
                                        # Si tenemos cantidad (índice 3)
                                        if len(row) > 3 and row[3]:
                                            try:
                                                kg_disponibles = row[3]  # Usar el mismo valor que cantidad
                                                sheets.values().update(
                                                    spreadsheetId=spreadsheet_id,
                                                    range=f"{sheet_name}!H{row_num}",  # H es kg_disponibles (columna 8)
                                                    valueInputOption="RAW",
                                                    body={"values": [[kg_disponibles]]}
                                                ).execute()
                                                logger.info(f"Actualizada kg_disponibles en fila {row_num}")
                                            except Exception as e:
                                                logger.error(f"Error al actualizar kg_disponibles en fila {row_num}: {e}")
                        
                        logger.info(f"Actualización de datos existentes completada para '{sheet_name}'")
                    else:
                        logger.info(f"No hay datos existentes que actualizar en '{sheet_name}'")
                    
                    # Si hay otras diferencias, actualizar las cabeceras
                    if values and values[0] != header:
                        logger.warning(f"Las cabeceras existentes no coinciden con las esperadas. Actualizando...")
                        sheets.values().update(
                            spreadsheetId=spreadsheet_id,
                            range=range_name,
                            valueInputOption="RAW",
                            body={"values": [header]}
                        ).execute()
                        logger.info(f"Cabeceras actualizadas en hoja '{sheet_name}'")
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
        row_data = []
        
        # Imprimir información detallada para depurar
        logger.info(f"Cabeceras para la hoja '{sheet_name}': {headers}")
        logger.info(f"Datos recibidos: {data}")
        
        # Verificar que todos los campos necesarios existan
        for header in headers:
            if header not in data or not data[header]:
                logger.warning(f"Campo '{header}' faltante o vacío en los datos. Usando valor por defecto.")
                
                # Valores por defecto según el campo
                if header == 'tipo_cafe':
                    data[header] = "No especificado"
                elif header in ['cantidad', 'precio', 'total', 'kg_disponibles', 'merma']:
                    data[header] = "0"
                elif header == 'fase_actual' and sheet_name == 'compras' and 'tipo_cafe' in data:
                    # Si es una compra, la fase inicial es el tipo de café
                    data[header] = data.get('tipo_cafe', "No especificado")
                else:
                    data[header] = ""
        
        # Pre-procesamiento específico para el campo de fecha
        # Para adelantos, asegurarnos de que las fechas tengan el formato correcto
        if sheet_name == 'adelantos':
            # Formatear explícitamente la fecha como texto para evitar que Sheets la convierta en número
            if 'fecha' in data and data['fecha']:
                # Asegurarse de que la fecha tiene el formato correcto (YYYY-MM-DD)
                # Si no sigue el formato, se deja como está
                if isinstance(data['fecha'], str) and len(data['fecha']) == 10 and data['fecha'][4] == '-' and data['fecha'][7] == '-':
                    # Prefijo con comilla simple para forzar formato de texto en Google Sheets
                    data['fecha'] = f"'{data['fecha']}"
                    logger.info(f"Fecha formateada como texto: {data['fecha']}")
            
            # Hacer lo mismo con la hora
            if 'hora' in data and data['hora']:
                # Asegurarse de que la hora tiene el formato correcto (HH:MM:SS)
                # Si no sigue el formato, se deja como está
                if isinstance(data['hora'], str) and len(data['hora']) == 8 and data['hora'][2] == ':' and data['hora'][5] == ':':
                    # Prefijo con comilla simple para forzar formato de texto
                    data['hora'] = f"'{data['hora']}"
                    logger.info(f"Hora formateada como texto: {data['hora']}")
        
        # Construir la fila de datos ordenada según las cabeceras
        for header in headers:
            row_data.append(data.get(header, ""))
        
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
        
        # Pre-procesamiento para campos específicos
        if sheet_name == 'adelantos' and column_name == 'fecha':
            # Asegurarse de que la fecha tiene el formato correcto (YYYY-MM-DD)
            if isinstance(value, str) and len(value) == 10 and value[4] == '-' and value[7] == '-':
                # Prefijo con comilla simple para forzar formato de texto en Google Sheets
                value = f"'{value}"
                logger.info(f"Fecha formateada como texto para actualización: {value}")
        
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

def es_transicion_valida(origen, destino):
    """Verifica si la transición de fase es válida
    
    Args:
        origen: Fase de origen
        destino: Fase de destino
        
    Returns:
        bool: True si la transición es válida, False en caso contrario
    """
    if origen not in TRANSICIONES_PERMITIDAS:
        return False
    
    return destino in TRANSICIONES_PERMITIDAS[origen]