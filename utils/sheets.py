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
FASES_CAFE = ["CEREZO", "MOTE", "PERGAMINO", "TOSTADO", "MOLIDO"]

# Definir transiciones válidas entre fases
TRANSICIONES_PERMITIDAS = {
    "CEREZO": ["MOTE"],
    "MOTE": ["PERGAMINO"],
    "PERGAMINO": ["TOSTADO", "MOLIDO"],  # Permitir transición directa a MOLIDO
    "TOSTADO": ["MOLIDO"]
}

# Cabeceras para las hojas
HEADERS = {
    "compras": ["id", "fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "preciototal", "notas", "registrado_por"],
    "proceso": ["fecha", "origen", "destino", "cantidad", "compras_ids", "merma", "notas", "registrado_por"],
    "gastos": ["fecha", "categoria", "monto", "descripcion", "registrado_por"],
    "ventas": ["fecha", "cliente", "tipo_cafe", "peso", "precio_kg", "total", "notas", "registrado_por"],
    "pedidos": ["fecha", "cliente", "tipo_cafe", "cantidad", "precio_kg", "total", "estado", "fecha_entrega", "notas", "registrado_por"],
    "adelantos": ["fecha", "hora", "cliente", "monto", "notas", "registrado_por"],
    "almacen": ["id", "compra_id", "fase", "fecha", "cantidad", "fase_actual", "kg_disponibles", "notas"]
}

# Variables globales para el servicio de Google Sheets
_sheet_service = None

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

def initialize_sheets():
    """Inicializa las hojas de Google Sheets con las cabeceras correctas"""
    try:
        sheets = get_sheet_service()
        spreadsheet_id = get_or_create_sheet()
        
        # Obtener todas las hojas existentes
        sheet_metadata = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        existing_sheets = {sheet['properties']['title'] for sheet in sheet_metadata.get('sheets', [])}
        
        # Para cada hoja definida en HEADERS
        for sheet_name, headers in HEADERS.items():
            # Verificar si la hoja existe
            if sheet_name not in existing_sheets:
                # Crear la hoja
                logger.info(f"Creando hoja '{sheet_name}'...")
                requests = [{
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }]
                sheets.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={'requests': requests}
                ).execute()
                
                # Verificar si la hoja se creó correctamente
                sheet_metadata = sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
                updated_existing_sheets = {sheet['properties']['title'] for sheet in sheet_metadata.get('sheets', [])}
                
                if sheet_name in updated_existing_sheets:
                    logger.info(f"Hoja '{sheet_name}' creada correctamente")
                else:
                    logger.error(f"Error al crear la hoja '{sheet_name}'")
                    continue
            
            # Verificar si la hoja tiene cabeceras
            range_name = f"{sheet_name}!A1:Z1"
            result = sheets.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values or len(values[0]) < len(headers):
                # Escribir las cabeceras
                logger.info(f"Escribiendo cabeceras para la hoja '{sheet_name}'...")
                sheets.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    body={"values": [headers]}
                ).execute()
                
                logger.info(f"Cabeceras para '{sheet_name}' actualizadas correctamente")
            else:
                logger.info(f"La hoja '{sheet_name}' ya tiene cabeceras")
            
            # Operaciones especiales por tipo de hoja
            if sheet_name == 'compras':
                # Para compras existentes, asegurarse de que tengan un ID único
                # Esto es para mantener compatibilidad con compras que no tenían ID
                compras = get_all_data('compras')
                for i, compra in enumerate(compras):
                    if not compra.get('id'):
                        # Generar un ID único
                        nuevo_id = generate_unique_id()
                        # Actualizar la compra
                        update_cell('compras', compra['_row_index'], 'id', nuevo_id)
                        logger.info(f"Asignado ID {nuevo_id} a compra existente (fila {compra['_row_index'] + 2})")
                    
                    # Migrar datos antiguos al nuevo formato: fase_actual y kg_disponibles van a almacen
                    if ('fase_actual' in compra or 'kg_disponibles' in compra) and compra.get('tipo_cafe'):
                        fase = compra.get('fase_actual', compra.get('tipo_cafe'))
                        kg_disponibles = safe_float(compra.get('kg_disponibles', compra.get('cantidad', 0)))
                        if kg_disponibles > 0:
                            # Crear registro en almacén para esta compra
                            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            append_data('almacen', {
                                'id': generate_almacen_id(),
                                'compra_id': compra.get('id'),
                                'fase': fase,
                                'fecha': now,
                                'cantidad': compra.get('cantidad', 0),
                                'fase_actual': fase,
                                'kg_disponibles': kg_disponibles,
                                'notas': f"Migración automática desde compra ID: {compra.get('id')}"
                            })
                            logger.info(f"Creado registro en almacén para compra {compra.get('id')} con {kg_disponibles} kg en fase {fase}")
            
            elif sheet_name == 'almacen':
                # Para el almacén, asegurarse de que todas las fases estén inicializadas
                almacen_data = get_all_data('almacen')
                fases_existentes = {str(item.get('fase', '')).strip().upper() for item in almacen_data}
                
                # Verificar si es necesario sincronizar
                fases_faltantes = set(FASES_CAFE) - fases_existentes
                if fases_faltantes:
                    logger.info(f"Inicializando fases faltantes en almacén: {fases_faltantes}")
                    
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for fase in fases_faltantes:
                        # Añadir la fase con cantidad 0
                        append_data('almacen', {
                            'id': generate_almacen_id(),
                            'compra_id': '',
                            'fase': fase,
                            'fecha': now,
                            'cantidad': 0,
                            'fase_actual': fase,
                            'kg_disponibles': 0,
                            'notas': 'Inicialización automática'
                        })
        
        logger.info("Inicialización de hojas completada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al inicializar las hojas: {e}")
        return False

def generate_unique_id(length=6):
    """
    Genera un ID único alfanumérico para compras
    
    Args:
        length: Longitud del ID (default: 6)
    
    Returns:
        str: ID único alfanumérico
    """
    # Caracteres permitidos (letras mayúsculas y números)
    chars = string.ascii_uppercase + string.digits
    
    # Generar un ID único con formato CP-XXXXXX (Café Purchase)
    unique_id = 'CP-' + ''.join(random.choice(chars) for _ in range(length))
    
    return unique_id

def generate_almacen_id(length=6):
    """
    Genera un ID único alfanumérico para registros del almacén
    
    Args:
        length: Longitud del ID (default: 6)
    
    Returns:
        str: ID único alfanumérico
    """
    # Caracteres permitidos (letras mayúsculas y números)
    chars = string.ascii_uppercase + string.digits
    
    # Generar un ID único con formato AL-XXXXXX (Almacén)
    unique_id = 'AL-' + ''.join(random.choice(chars) for _ in range(length))
    
    return unique_id

def format_date_for_sheets(date_str):
    """
    Formatea una fecha para evitar que Google Sheets la convierta automáticamente
    
    Args:
        date_str: Fecha en formato YYYY-MM-DD
    
    Returns:
        str: Fecha formateada para Google Sheets
    """
    # Verificar formato
    if isinstance(date_str, str) and len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
        # Prefijo con comilla simple para forzar formato de texto en Google Sheets
        return f"'{date_str}'"
    return date_str

def append_data(sheet_name, data):
    """Añade una fila de datos a la hoja especificada"""
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        service = get_sheet_service()
        
        # Para compras, asegurar que tenga un ID único
        if sheet_name == 'compras' and 'id' not in data:
            data['id'] = generate_unique_id()
            logger.info(f"Generado ID único para compra: {data['id']}")
            
            # Calcular precio total si no está especificado
            if 'preciototal' not in data and 'cantidad' in data and 'precio' in data:
                try:
                    cantidad = float(str(data.get('cantidad', '0')).replace(',', '.'))
                    precio = float(str(data.get('precio', '0')).replace(',', '.'))
                    data['preciototal'] = str(round(cantidad * precio, 2))
                    logger.info(f"Calculado precio total para compra: {data['preciototal']}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error al calcular precio total: {e}")
        
        # Para almacén, asegurar que tenga un ID único
        if sheet_name == 'almacen' and 'id' not in data:
            data['id'] = generate_almacen_id()
            logger.info(f"Generado ID único para almacén: {data['id']}")
            
            # Si no tiene fecha, agregar la fecha actual
            if 'fecha' not in data or not data['fecha']:
                data['fecha'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
                elif header in ['cantidad', 'precio', 'total', 'kg_disponibles', 'merma', 'preciototal']:
                    data[header] = "0"
                elif header == 'fase_actual' and sheet_name == 'almacen' and 'fase' in data:
                    # Si es almacén, la fase_actual es la misma que la fase
                    data[header] = data.get('fase', "")
                else:
                    data[header] = ""
        
        # Pre-procesamiento específico para el campo de fecha
        # Para adelantos, asegurarnos de que las fechas tengan el formato correcto
        if sheet_name == 'adelantos':
            # Formatear explícitamente la fecha como texto para evitar que Sheets la convierta en número
            if 'fecha' in data and data['fecha']:
                data['fecha'] = format_date_for_sheets(data['fecha'])
            
            # Hacer lo mismo con la hora
            if 'hora' in data and data['hora']:
                # Asegurarse de que la hora tiene el formato correcto (HH:MM:SS)
                # Si no sigue el formato, se deja como está
                if isinstance(data['hora'], str) and len(data['hora']) == 8 and data['hora'][2] == ':' and data['hora'][5] == ':':
                    # Prefijo con comilla simple para forzar formato de texto
                    data['hora'] = f"'{data['hora']}'"
                    logger.info(f"Hora formateada como texto: {data['hora']}")
        
        # Construir la fila de datos ordenada según las cabeceras
        for header in headers:
            row_data.append(data.get(header, ""))
        
        logger.info(f"Añadiendo datos a '{sheet_name}': {data}")
        logger.info(f"Datos formateados para Sheets: {row_data}")
        
        # ENFOQUE COMPLETAMENTE NUEVO
        try:
            # 1. Primero obtenemos el ID de la hoja
            sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheet_metadata.get('sheets', '')
            sheet_id = None
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                logger.error(f"No se pudo encontrar el ID de la hoja '{sheet_name}'")
                return False
            
            logger.info(f"Usando sheet_id: {sheet_id} para '{sheet_name}'")
            
            # 2. Usamos appendCells directamente en el API en lugar del helper append()
            # Este enfoque evita completamente el problema de 'Resource' object has no attribute 'values'
            request_body = {
                "requests": [
                    {
                        "appendCells": {
                            "sheetId": sheet_id,
                            "rows": [
                                {
                                    "values": [
                                        {"userEnteredValue": {"stringValue": str(value) if value is not None else ""}} 
                                        for value in row_data
                                    ]
                                }
                            ],
                            "fields": "userEnteredValue"
                        }
                    }
                ]
            }
            
            # Ejecutar el batchUpdate con la solicitud de appendCells
            response = service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request_body
            ).execute()
            
            logger.info(f"Datos añadidos correctamente a '{sheet_name}' usando appendCells")
            
            # Si se agregó exitosamente una compra, crear también el registro en almacén
            if sheet_name == 'compras' and 'tipo_cafe' in data and 'cantidad' in data:
                try:
                    # Extraer datos de la compra
                    fase = data['tipo_cafe']
                    cantidad = float(str(data.get('cantidad', '0')).replace(',', '.'))
                    
                    # Crear registro en almacén para esta compra
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Registro de almacén para la nueva compra
                    nuevo_almacen = {
                        'id': generate_almacen_id(),
                        'compra_id': data.get('id', ''),
                        'fase': fase,
                        'fecha': now,
                        'cantidad': cantidad,
                        'fase_actual': fase,
                        'kg_disponibles': cantidad,
                        'notas': f"Compra inicial ID: {data.get('id', 'sin ID')}"
                    }
                    
                    # Añadir a la hoja de almacén
                    result_almacen = append_data('almacen', nuevo_almacen)
                    
                    if result_almacen:
                        logger.info(f"Registro de almacén creado para compra {data.get('id')}: {cantidad} kg de {fase}")
                    else:
                        logger.warning(f"No se pudo crear registro en almacén para compra {data.get('id')}")
                    
                except Exception as e:
                    logger.error(f"Error al crear registro en almacén después de compra: {e}")
                    # No fallar si hay un error en el almacén, solo registrar
            
            return True
        except Exception as e:
            logger.error(f"Error al usar appendCells: {e}")
            
            # Si falla el método principal, intentar un método de respaldo
            try:
                logger.info("Intentando método de respaldo con batchUpdate...")
                
                # Obtener todas las filas para determinar el índice de la próxima fila
                response = service.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A:A"
                ).execute()
                
                # Determinar la próxima fila (la cantidad de filas actuales + 1)
                next_row = len(response.get('values', [])) + 1
                logger.info(f"Siguiente fila disponible: {next_row}")
                
                # Actualizar esa fila específica
                update_response = service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!A{next_row}:Z{next_row}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [row_data]}
                ).execute()
                
                logger.info(f"Datos añadidos correctamente a '{sheet_name}' en la fila {next_row} usando método de respaldo")
                return True
            except Exception as backup_error:
                logger.error(f"Error con método de respaldo: {backup_error}")
                
                # Último intento: crear fila por fila manualmente (enfoque extremadamente básico)
                try:
                    logger.info("Intentando método de último recurso...")
                    
                    # Construir una solicitud sin usar métodos auxiliares
                    from googleapiclient.http import build_http
                    
                    # Crear el objeto Http
                    http = build_http()
                    
                    # URL para el API de Sheets
                    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A:A:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
                    
                    # Datos a enviar
                    data = {
                        "values": [row_data]
                    }
                    
                    # Headers con token de autorización
                    headers = {
                        "Authorization": f"Bearer {service._http.credentials.token}",
                        "Content-Type": "application/json"
                    }
                    
                    # Realizar la solicitud POST
                    import requests
                    response = requests.post(url, json=data, headers=headers)
                    
                    if response.status_code == 200:
                        logger.info(f"Datos añadidos correctamente a '{sheet_name}' usando método de último recurso")
                        return True
                    else:
                        logger.error(f"Error con método de último recurso: {response.text}")
                        return False
                except Exception as final_error:
                    logger.error(f"Error con método de último recurso: {final_error}")
                    return False
    except Exception as e:
        logger.error(f"Error global al añadir datos a {sheet_name}: {e}")
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
        service = get_sheet_service()
        
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
        if (sheet_name == 'adelantos' and column_name == 'fecha') or column_name == 'fecha':
            value = format_date_for_sheets(value)
        
        logger.info(f"Actualizando celda {cell_reference} en hoja '{sheet_name}' con valor: {value}")
        
        # ENFOQUE MÁS ROBUSTO: Usar batchUpdate con updateCells
        try:
            # 1. Obtener el ID de la hoja
            sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            sheets = sheet_metadata.get('sheets', '')
            sheet_id = None
            for sheet in sheets:
                if sheet['properties']['title'] == sheet_name:
                    sheet_id = sheet['properties']['sheetId']
                    break
            
            if sheet_id is None:
                logger.error(f"No se pudo encontrar el ID de la hoja '{sheet_name}'")
                return False
            
            # 2. Crear la solicitud de actualización usando updateCells
            request_body = {
                "requests": [
                    {
                        "updateCells": {
                            "range": {
                                "sheetId": sheet_id,
                                "startRowIndex": real_row - 1,  # Índice basado en 0
                                "endRowIndex": real_row,
                                "startColumnIndex": column_index,
                                "endColumnIndex": column_index + 1
                            },
                            "rows": [
                                {
                                    "values": [
                                        {
                                            "userEnteredValue": {
                                                "stringValue": str(value) if value is not None else ""
                                            }
                                        }
                                    ]
                                }
                            ],
                            "fields": "userEnteredValue"
                        }
                    }
                ]
            }
            
            # 3. Ejecutar la solicitud
            response = service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=request_body
            ).execute()
            
            logger.info(f"Celda actualizada correctamente con batchUpdate: {sheet_name}!{cell_reference}")
            return True
        except Exception as e:
            logger.error(f"Error al actualizar celda con batchUpdate: {e}")
            
            # Método alternativo de respaldo
            try:
                logger.info("Intentando método alternativo para actualizar celda...")
                
                # Usar el método tradicional values().update()
                service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"{sheet_name}!{cell_reference}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [[value]]}
                ).execute()
                
                logger.info(f"Celda actualizada correctamente con método alternativo: {sheet_name}!{cell_reference}")
                return True
            except Exception as backup_error:
                logger.error(f"Error con método alternativo para actualizar celda: {backup_error}")
                return False
    except Exception as e:
        logger.error(f"Error global al actualizar celda: {e}")
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
        # Para cada clave:valor de filtro, verificar coincidencia
        filtered_data = []
        for row in all_data:
            match = True
            for key, value in filters.items():
                # Normalizar valores para comparación (convertir a mayúsculas y eliminar espacios adicionales)
                row_value = str(row.get(key, '')).strip().upper()
                filter_value = str(value).strip().upper()
                
                if row_value != filter_value:
                    match = False
                    break
            
            if match:
                filtered_data.append(row)
    
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

def get_compras_por_fase(fase):
    """
    Obtiene todas las compras en una fase específica con kg disponibles
    
    Args:
        fase: Fase actual del café (CEREZO, MOTE, PERGAMINO, etc.)
        
    Returns:
        Lista de compras en la fase especificada que aún tienen kg disponibles
    """
    try:
        logger.info(f"Buscando compras en fase: {fase}")
        
        # Buscar en almacén los registros con la fase actual especificada
        almacen_data = get_filtered_data('almacen', {'fase_actual': fase})
        
        if not almacen_data:
            logger.warning(f"No hay registros en almacén para la fase {fase}")
            return []
        
        # Filtrar solo aquellos que tienen kg disponibles
        almacen_con_disponible = []
        for registro in almacen_data:
            try:
                kg_disponibles = float(str(registro.get('kg_disponibles', '0')).replace(',', '.'))
                if kg_disponibles > 0:
                    almacen_con_disponible.append(registro)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error al convertir kg_disponibles: {e}. Valor: {registro.get('kg_disponibles')}")
        
        if not almacen_con_disponible:
            logger.warning(f"No hay registros en almacén con kg disponibles para la fase {fase}")
            return []
        
        # Obtener las compras correspondientes
        all_compras = get_all_data('compras')
        compras_disponibles = []
        
        for registro_almacen in almacen_con_disponible:
            compra_id = registro_almacen.get('compra_id', '')
            if not compra_id:
                continue
            
            # Buscar la compra correspondiente
            for compra in all_compras:
                if compra.get('id') == compra_id:
                    # Añadir kg_disponibles del almacén a la compra
                    compra_con_disponible = compra.copy()
                    compra_con_disponible['kg_disponibles'] = registro_almacen.get('kg_disponibles', '0')
                    compra_con_disponible['almacen_registro_id'] = registro_almacen.get('id', '')
                    compra_con_disponible['almacen_row_index'] = registro_almacen.get('_row_index', 0)
                    compras_disponibles.append(compra_con_disponible)
                    break
        
        logger.info(f"Total compras encontradas en fase {fase}: {len(compras_disponibles)}")
        return compras_disponibles
    except Exception as e:
        logger.error(f"Error al obtener compras en fase {fase}: {e}")
        return []

def get_almacen_cantidad(fase):
    """
    Obtiene la cantidad disponible de una fase específica del almacén
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, etc.)
    
    Returns:
        float: Cantidad disponible en kg
    """
    try:
        # Normalizar fase para búsqueda
        fase_buscada = fase.strip().upper()
        
        # Obtener datos de almacén filtrados por fase_actual
        almacen_data = get_filtered_data('almacen', {'fase_actual': fase_buscada})
        
        if not almacen_data:
            logger.warning(f"No se encontró la fase {fase_buscada} en el almacén")
            return 0.0
        
        # Calcular la suma total de kg disponibles
        total_disponible = 0.0
        for registro in almacen_data:
            try:
                kg_disponibles = float(str(registro.get('kg_disponibles', '0')).replace(',', '.'))
                total_disponible += kg_disponibles
            except (ValueError, TypeError) as e:
                logger.error(f"Error al convertir kg_disponibles: {e}")
        
        logger.info(f"Cantidad total en almacén para fase {fase_buscada}: {total_disponible} kg")
        return total_disponible
    except Exception as e:
        logger.error(f"Error al obtener cantidad en almacén para fase {fase}: {e}")
        return 0.0

def update_almacen(fase, cantidad_cambio, operacion="sumar", notas="", compra_id=""):
    """
    Actualiza la cantidad disponible en el almacén para una fase específica
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, etc.)
        cantidad_cambio: Cantidad a sumar o restar
        operacion: "sumar" para añadir, "restar" para disminuir, "establecer" para fijar valor
        notas: Notas adicionales sobre la operación
        compra_id: ID de compra relacionada (si aplica)
    
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        import datetime
        
        logger.info(f"Actualizando almacén - Fase: {fase}, Cambio: {cantidad_cambio} kg, Operación: {operacion}, Compra ID: {compra_id}")
        
        # Normalizar fase
        fase_normalizada = fase.strip().upper()
        
        # Crear nuevo registro para esta operación de almacén
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        nueva_entrada = {
            "id": generate_almacen_id(),
            "compra_id": compra_id,
            "fase": fase_normalizada,
            "fecha": now,
            "cantidad": cantidad_cambio if operacion in ["sumar", "establecer"] else -cantidad_cambio,
            "fase_actual": fase_normalizada,
            "kg_disponibles": cantidad_cambio if operacion in ["sumar", "establecer"] else 0,
            "notas": f"Operación: {operacion}. {notas}"
        }
        
        # Añadir a la hoja
        resultado = append_data("almacen", nueva_entrada)
        
        if resultado:
            logger.info(f"Nuevo registro de almacén creado correctamente: {nueva_entrada['id']}")
            return True
        else:
            logger.error(f"Error al crear nuevo registro de almacén")
            return False
    except Exception as e:
        logger.error(f"Error al actualizar almacén: {e}")
        return False

def actualizar_almacen_desde_proceso(origen, destino, cantidad, merma):
    """
    Actualiza el almacén basado en un proceso de transformación
    
    Args:
        origen: Fase de origen del café
        destino: Fase de destino del café
        cantidad: Cantidad procesada en kg
        merma: Cantidad de merma en kg
    
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        logger.info(f"Actualizando almacén desde proceso - Origen: {origen}, Destino: {destino}, Cantidad: {cantidad} kg, Merma: {merma} kg")
        
        # 1. Restar la cantidad procesada de la fase de origen
        resultado_origen = update_almacen(
            fase=origen,
            cantidad_cambio=cantidad,
            operacion="restar",
            notas=f"Proceso a {destino}"
        )
        
        # 2. Calcular cantidad resultante (restando merma)
        cantidad_resultante = max(0, float(cantidad) - float(merma))
        
        # 3. Sumar la cantidad resultante a la fase de destino
        resultado_destino = update_almacen(
            fase=destino,
            cantidad_cambio=cantidad_resultante,
            operacion="sumar",
            notas=f"Procesado desde {origen}"
        )
        
        return resultado_origen and resultado_destino
    except Exception as e:
        logger.error(f"Error al actualizar almacén desde proceso: {e}")
        return False

def sincronizar_almacen_con_compras():
    """
    Sincroniza el almacén con las existencias actuales en las compras.
    Útil para inicializar o corregir discrepancias.
    
    Returns:
        bool: True si se sincronizó correctamente, False en caso contrario
    """
    try:
        logger.info("Iniciando sincronización de almacén con compras")
        
        # Obtener todas las compras
        compras = get_all_data('compras')
        
        # Agrupar compras por tipo_cafe/fase
        compras_por_fase = {}
        for compra in compras:
            tipo_cafe = compra.get('tipo_cafe', '').strip().upper()
            if tipo_cafe and tipo_cafe in FASES_CAFE:
                if tipo_cafe not in compras_por_fase:
                    compras_por_fase[tipo_cafe] = []
                compras_por_fase[tipo_cafe].append(compra)
        
        # Crear nuevos registros en almacén para cada compra
        resultados = []
        for fase, compras_list in compras_por_fase.items():
            for compra in compras_list:
                try:
                    # Calcular cantidad
                    cantidad = safe_float(compra.get('cantidad', 0))
                    
                    # Verificar si ya existe un registro en almacén para esta compra
                    compra_id = compra.get('id', '')
                    if compra_id:
                        almacen_existente = get_filtered_data('almacen', {'compra_id': compra_id})
                        if almacen_existente:
                            logger.info(f"Ya existe registro en almacén para compra {compra_id}")
                            continue
                    
                    # Crear registro en almacén
                    if cantidad > 0:
                        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        resultado = append_data('almacen', {
                            'id': generate_almacen_id(),
                            'compra_id': compra_id,
                            'fase': fase,
                            'fecha': now,
                            'cantidad': cantidad,
                            'fase_actual': fase,
                            'kg_disponibles': cantidad,
                            'notas': f"Sincronización automática - Compra ID: {compra_id}"
                        })
                        resultados.append(resultado)
                        if resultado:
                            logger.info(f"Creado registro en almacén para compra {compra_id}")
                        else:
                            logger.warning(f"Error al crear registro en almacén para compra {compra_id}")
                except Exception as e:
                    logger.error(f"Error al procesar compra {compra.get('id', '')}: {e}")
                    resultados.append(False)
        
        # Verificar resultados
        if all(resultados):
            logger.info("Sincronización de almacén completada correctamente")
            return True
        else:
            logger.warning(f"Sincronización parcial: {resultados.count(True)}/{len(resultados)} operaciones exitosas")
            return resultados.count(True) > 0
    except Exception as e:
        logger.error(f"Error al sincronizar almacén con compras: {e}")
        return False

def leer_almacen_para_proceso():
    """
    Lee los registros de almacén para mostrarlos en el comando /proceso
    
    Returns:
        dict: Diccionario con fases y cantidades disponibles
    """
    try:
        logger.info("Leyendo registros de almacén para proceso")
        
        # Obtener todos los registros de almacén
        almacen_data = get_all_data('almacen')
        
        # Agrupar y sumar por fase_actual
        resultados = {}
        for registro in almacen_data:
            fase_actual = str(registro.get('fase_actual', '')).strip().upper()
            if fase_actual in FASES_CAFE:
                # Sumar las cantidades disponibles por fase
                try:
                    kg_disponibles = float(str(registro.get('kg_disponibles', '0')).replace(',', '.'))
                    if fase_actual not in resultados:
                        resultados[fase_actual] = {
                            'cantidad_total': 0,
                            'registros': []
                        }
                    
                    if kg_disponibles > 0:
                        resultados[fase_actual]['cantidad_total'] += kg_disponibles
                        resultados[fase_actual]['registros'].append(registro)
                except (ValueError, TypeError) as e:
                    logger.error(f"Error al procesar kg_disponibles en almacén: {e}")
        
        return resultados
    except Exception as e:
        logger.error(f"Error al leer almacén para proceso: {e}")
        return {}

def safe_float(value):
    """
    Convierte un valor a float de forma segura
    
    Args:
        value: Valor a convertir
    
    Returns:
        float: Valor convertido o 0.0 en caso de error
    """
    try:
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            return float(value.replace(',', '.'))
        return 0.0
    except (ValueError, TypeError):
        return 0.0