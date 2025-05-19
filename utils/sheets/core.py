"""
Módulo con las operaciones básicas para Google Sheets.
"""
import logging
from typing import Dict, List, Any, Optional, Union
import requests

from utils.sheets.constants import HEADERS
from utils.sheets.service import get_sheet_service, get_or_create_sheet, get_sheet_id, get_sheets_initialized, set_sheets_initialized
from utils.sheets.utils import format_date_for_sheets, generate_unique_id, generate_almacen_id, get_current_datetime_str, safe_float

# Configurar logging
logger = logging.getLogger(__name__)

def initialize_sheets():
    """
    Inicializa las hojas de Google Sheets con las cabeceras correctas.
    
    Returns:
        bool: True si se inicializaron correctamente, False en caso contrario
    """
    # Si ya se inicializaron las hojas en esta sesión, no volver a hacerlo
    if get_sheets_initialized():
        logger.info("Las hojas ya fueron inicializadas en esta sesión, omitiendo...")
        return True
    
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
            result = sheets.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values or len(values[0]) < len(headers):
                # Escribir las cabeceras
                logger.info(f"Escribiendo cabeceras para la hoja '{sheet_name}'...")
                sheets.spreadsheets().values().update(
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
                        
                        # Verificar si ya existe un registro en almacén para esta compra
                        compra_id = compra.get('id', '')
                        almacen_existente = []
                        if compra_id:
                            almacen_existente = get_filtered_data('almacen', {'compra_id': compra_id})
                        
                        # Solo crear registro si no existe y si hay kg disponibles
                        if not almacen_existente and kg_disponibles > 0:
                            now = get_current_datetime_str()
                            append_data('almacen', {
                                'id': generate_almacen_id(),
                                'compra_id': compra_id,
                                'tipo_cafe_origen': fase,
                                'fecha': now,
                                'cantidad': compra.get('cantidad', 0),
                                'fase_actual': fase,
                                'cantidad_actual': kg_disponibles,
                                'notas': f"Migración automática desde compra ID: {compra_id}",
                                'fecha_actualizacion': now
                            })
                            logger.info(f"Creado registro en almacén para compra {compra_id} con {kg_disponibles} kg en fase {fase}")
        
        # Marcar hojas como inicializadas para esta sesión
        set_sheets_initialized(True)
        
        logger.info("Inicialización de hojas completada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al inicializar las hojas: {e}")
        return False

def append_data(sheet_name, data):
    """
    Añade una fila de datos a la hoja especificada.
    
    Args:
        sheet_name: Nombre de la hoja
        data: Diccionario con los datos a añadir
        
    Returns:
        bool: True si se añadieron los datos correctamente, False en caso contrario
    """
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        service = get_sheet_service()
        
        # Para compras, asegurar que tenga un ID único
        if sheet_name == 'compras':
            # Siempre asignar un ID único, incluso si ya existe uno
            if not data.get('id'):
                data['id'] = generate_unique_id()
                logger.info(f"Generado ID único para compra: {data['id']}")
            
            # Calcular precio total si no está especificado o es 0
            if ('preciototal' not in data or not data.get('preciototal') or safe_float(data.get('preciototal')) == 0) and 'cantidad' in data and 'precio' in data:
                try:
                    cantidad = float(str(data.get('cantidad', '0')).replace(',', '.'))
                    precio = float(str(data.get('precio', '0')).replace(',', '.'))
                    # Asegurar que el precio no sea 0
                    if precio <= 0:
                        logger.warning(f"Precio está configurado a {precio}, podría ser un error. Se guardará como está.")
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
                data['fecha'] = get_current_datetime_str()
            
            # Agregar fecha de actualización si no existe
            if 'fecha_actualizacion' not in data or not data['fecha_actualizacion']:
                data['fecha_actualizacion'] = get_current_datetime_str()
                logger.info(f"Añadida fecha de actualización: {data['fecha_actualizacion']}")
        
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
                if header == 'tipo_cafe' or header == 'tipo_cafe_origen':
                    data[header] = "No especificado"
                elif header in ['cantidad', 'precio', 'total', 'cantidad_actual', 'merma', 'merma_estimada', 'cantidad_resultante', 'cantidad_resultante_esperada', 'preciototal']:
                    data[header] = "0"
                elif header == 'fase_actual' and sheet_name == 'almacen' and 'tipo_cafe_origen' in data:
                    # Si es almacén, la fase_actual es la misma que la fase
                    data[header] = data.get('tipo_cafe_origen', "")
                elif header == 'fecha_actualizacion' and sheet_name == 'almacen':
                    # Fecha de actualización para registros de almacén
                    data[header] = get_current_datetime_str()
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
        
        # ENFOQUE USANDO APPENDCELLS (más robusto)
        try:
            # 1. Obtener el ID de la hoja
            sheet_id = get_sheet_id(sheet_name)
            
            if sheet_id is None:
                logger.error(f"No se pudo encontrar el ID de la hoja '{sheet_name}'")
                return False
            
            logger.info(f"Usando sheet_id: {sheet_id} para '{sheet_name}'")
            
            # 2. Usamos appendCells directamente en el API
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
            # SOLO crear registro en almacén si es una compra nueva y no si ya estamos creando un registro de almacén
            # para evitar duplicación
            if sheet_name == 'compras' and 'tipo_cafe' in data and 'cantidad' in data:
                try:
                    # Extraer datos de la compra
                    fase = data['tipo_cafe']
                    cantidad = float(str(data.get('cantidad', '0')).replace(',', '.'))
                    compra_id = data.get('id', '')
                    
                    # Verificar si ya existe un registro en almacén para esta compra
                    almacen_existente = []
                    if compra_id:
                        almacen_existente = get_filtered_data('almacen', {'compra_id': compra_id})
                    
                    # SOLO crear registro si no existe y si hay kg disponibles
                    if not almacen_existente and cantidad > 0:
                        # Crear registro en almacén para esta compra
                        now = get_current_datetime_str()
                        
                        # Registro de almacén para la nueva compra
                        nuevo_almacen = {
                            'id': generate_almacen_id(),
                            'compra_id': data.get('id', ''),
                            'tipo_cafe_origen': fase,
                            'fecha': now,
                            'cantidad': cantidad,
                            'fase_actual': fase,
                            'cantidad_actual': cantidad,
                            'notas': f"Compra inicial ID: {data.get('id', 'sin ID')}",
                            'fecha_actualizacion': now
                        }
                        
                        # Añadir a la hoja de almacén
                        result_almacen = append_data('almacen', nuevo_almacen)
                        
                        if result_almacen:
                            logger.info(f"Registro de almacén creado para compra {data.get('id')}: {cantidad} kg de {fase}")
                        else:
                            logger.warning(f"No se pudo crear registro en almacén para compra {data.get('id')}")
                    else:
                        if almacen_existente:
                            logger.info(f"Ya existe un registro en almacén para la compra {compra_id}, no se creará otro")
                    
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
                    
                    # URL para el API de Sheets
                    url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}!A:A:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
                    
                    # Datos a enviar
                    data_to_send = {
                        "values": [row_data]
                    }
                    
                    # Headers con token de autorización
                    headers = {
                        "Authorization": f"Bearer {service._http.credentials.token}",
                        "Content-Type": "application/json"
                    }
                    
                    # Realizar la solicitud POST
                    response = requests.post(url, json=data_to_send, headers=headers)
                    
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
    """
    Actualiza una celda específica en la hoja de cálculo.
    
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
            sheet_id = get_sheet_id(sheet_name)
            
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
    """
    Obtiene todos los datos de la hoja especificada.
    
    Args:
        sheet_name: Nombre de la hoja
        
    Returns:
        List[Dict]: Lista de diccionarios con los datos
    """
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        range_name = f"{sheet_name}!A:Z"
        
        # Usar la llamada directa a sheets.spreadsheets().values().get()
        result = None
        try:
            result = sheets.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
        except Exception as e:
            logger.error(f"Error al ejecutar values().get() para {sheet_name}: {e}")
            # Si hay un error específico con values(), intentar otra aproximación
            return handle_values_attribute_error(sheet_name, spreadsheet_id, sheets)
        
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

def handle_values_attribute_error(sheet_name, spreadsheet_id, sheets_service):
    """
    Maneja el error 'Resource' object has no attribute 'values'.
    
    Args:
        sheet_name: Nombre de la hoja
        spreadsheet_id: ID del spreadsheet
        sheets_service: Servicio de Google Sheets
        
    Returns:
        List[Dict]: Lista de diccionarios con los datos
    """
    logger.info(f"Usando método alternativo para obtener datos de la hoja '{sheet_name}'")
    
    try:
        # 1. Obtener metadatos de la hoja
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        target_sheet = None
        
        # Buscar la hoja específica
        for sheet in sheet_metadata.get('sheets', []):
            if sheet['properties']['title'] == sheet_name:
                target_sheet = sheet
                break
        
        if not target_sheet:
            logger.warning(f"No se encontró la hoja '{sheet_name}' en el spreadsheet")
            return []
        
        # 2. Usar batchGet para obtener datos
        # Este método es más robusto y evita usar directamente el atributo 'values'
        result = sheets_service.spreadsheets().values().batchGet(
            spreadsheetId=spreadsheet_id,
            ranges=[f"{sheet_name}!A:Z"]
        ).execute()
        
        # Extraer los valores del resultado
        value_ranges = result.get('valueRanges', [])
        if not value_ranges or 'values' not in value_ranges[0]:
            logger.warning(f"No se encontraron datos en la hoja '{sheet_name}'")
            return []
        
        values = value_ranges[0]['values']
        
        # Procesar los valores como antes
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
        
        logger.info(f"Obtenidos {len(rows)} registros de '{sheet_name}' usando método alternativo")
        return rows
        
    except Exception as e:
        logger.error(f"Error en método alternativo para obtener datos: {e}")
        return []

def get_filtered_data(sheet_name, filters=None, days=None):
    """
    Obtiene datos filtrados de la hoja especificada.
    
    Args:
        sheet_name: Nombre de la hoja
        filters: Diccionario de filtros campo:valor
        days: Si se proporciona, filtra por entradas en los últimos X días
        
    Returns:
        List[Dict]: Lista de diccionarios con los datos filtrados
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