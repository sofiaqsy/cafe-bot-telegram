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

# Cabeceras para las hojas - Actualizada la estructura del almacén
HEADERS = {
    "compras": ["id", "fecha", "proveedor", "tipo_cafe", "fase_actual", "cantidad", "kg_disponibles", "precio", "total", "notas", "registrado_por"],
    "proceso": ["fecha", "origen", "destino", "cantidad", "compras_ids", "merma", "notas", "registrado_por"],
    "gastos": ["fecha", "categoria", "monto", "descripcion", "registrado_por"],
    "ventas": ["fecha", "cliente", "tipo_cafe", "peso", "precio_kg", "total", "notas", "registrado_por"],
    "pedidos": ["fecha", "cliente", "tipo_cafe", "cantidad", "precio_kg", "total", "estado", "fecha_entrega", "notas", "registrado_por"],
    "adelantos": ["fecha", "hora", "cliente", "monto", "notas", "registrado_por"],
    "almacen": ["id", "compra_id", "fecha", "fase_actual", "cantidad_kg", "ultima_actualizacion", "notas", "registrado_por"]
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
                        nuevo_id = generate_unique_id('CP')
                        # Actualizar la compra
                        update_cell('compras', compra['_row_index'], 'id', nuevo_id)
                        logger.info(f"Asignado ID {nuevo_id} a compra existente (fila {compra['_row_index'] + 2})")
            
            elif sheet_name == 'almacen':
                # Para el almacén, revisamos si necesita migración
                almacen_data = get_all_data('almacen')
                
                # Verificar si el almacén tiene la nueva estructura
                almacen_necesita_migracion = False
                
                if almacen_data:
                    # Comprobar si tiene la nueva estructura mirando las columnas de la primera fila
                    primera_fila = almacen_data[0] if almacen_data else {}
                    # Si no tiene id o compra_id, necesita migración
                    if 'id' not in primera_fila or 'compra_id' not in primera_fila:
                        almacen_necesita_migracion = True
                        logger.info("El almacén necesita migración a la nueva estructura")
                
                # Realizar la migración si es necesario
                if almacen_necesita_migracion:
                    logger.info("Iniciando migración del almacén a la nueva estructura...")
                    migrate_almacen()
                
                # Asegurarse de que todas las fases estén inicializadas en el almacén
                inicializar_fases_almacen()
        
        logger.info("Inicialización de hojas completada correctamente")
        return True
    except Exception as e:
        logger.error(f"Error al inicializar las hojas: {e}")
        return False

def migrate_almacen():
    """Migra la estructura del almacén del formato antiguo al nuevo"""
    try:
        logger.info("Iniciando migración del almacén a nueva estructura...")
        
        # 1. Obtener todos los datos actuales del almacén
        old_almacen_data = get_all_data('almacen')
        
        if not old_almacen_data:
            logger.info("No hay datos en el almacén para migrar")
            return True
        
        # 2. Crear una nueva hoja temporal para el almacén con la nueva estructura
        service = get_sheet_service()
        spreadsheet_id = get_or_create_sheet()
        
        # Crear una hoja temporal para la migración
        temp_sheet_name = f"almacen_new_{int(datetime.datetime.now().timestamp())}"
        requests = [{
            'addSheet': {
                'properties': {
                    'title': temp_sheet_name
                }
            }
        }]
        
        sheet_response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': requests}
        ).execute()
        
        # Escribir las nuevas cabeceras
        range_name = f"{temp_sheet_name}!A1:Z1"
        service.values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": [HEADERS["almacen"]]}
        ).execute()
        
        # 3. Migrar los datos existentes al nuevo formato
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_rows = []
        
        for old_row in old_almacen_data:
            # Crear un nuevo registro con la nueva estructura
            new_row = {
                "id": generate_unique_id('AL'),  # Generar un nuevo ID para el almacén
                "compra_id": "",                  # No podemos saber de qué compra vino en la migración
                "fecha": now,                     # Fecha actual
                "fase_actual": old_row.get('fase', ''),  # Mantener la fase
                "cantidad_kg": old_row.get('cantidad', 0),  # Mantener la cantidad
                "ultima_actualizacion": now,      # Actualizar a ahora
                "notas": f"Migrado de la estructura anterior. Notas originales: {old_row.get('notas', '')}",
                "registrado_por": "sistema_migracion"
            }
            new_rows.append(new_row)
        
        # 4. Guardar los nuevos datos en la hoja temporal
        for row in new_rows:
            # Convertir a lista según el nuevo orden de cabeceras
            row_data = []
            for header in HEADERS["almacen"]:
                row_data.append(row.get(header, ""))
            
            # Añadir a la hoja temporal
            next_row = len(service.values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{temp_sheet_name}!A:A"
            ).execute().get('values', [])) + 1
            
            service.values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{temp_sheet_name}!A{next_row}:Z{next_row}",
                valueInputOption="USER_ENTERED",
                body={"values": [row_data]}
            ).execute()
        
        # 5. Renombrar la hoja antigua a un nombre de respaldo
        backup_sheet_name = f"almacen_backup_{int(datetime.datetime.now().timestamp())}"
        
        # Primero, obtener el ID de las hojas
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', [])
        
        almacen_sheet_id = None
        temp_sheet_id = None
        
        for sheet in sheets:
            if sheet['properties']['title'] == 'almacen':
                almacen_sheet_id = sheet['properties']['sheetId']
            elif sheet['properties']['title'] == temp_sheet_name:
                temp_sheet_id = sheet['properties']['sheetId']
        
        if not almacen_sheet_id or not temp_sheet_id:
            raise ValueError("No se pudieron encontrar las hojas necesarias para la migración")
        
        # Renombrar la hoja antigua a backup
        rename_requests = [{
            'updateSheetProperties': {
                'properties': {
                    'sheetId': almacen_sheet_id,
                    'title': backup_sheet_name
                },
                'fields': 'title'
            }
        }]
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': rename_requests}
        ).execute()
        
        # 6. Renombrar la hoja temporal al nombre original
        rename_requests = [{
            'updateSheetProperties': {
                'properties': {
                    'sheetId': temp_sheet_id,
                    'title': 'almacen'
                },
                'fields': 'title'
            }
        }]
        
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={'requests': rename_requests}
        ).execute()
        
        logger.info(f"Migración del almacén completada. Backup guardado en '{backup_sheet_name}'")
        return True
    
    except Exception as e:
        logger.error(f"Error al migrar el almacén: {e}")
        return False

def inicializar_fases_almacen():
    """Inicializa las fases en el almacén si no existen"""
    try:
        almacen_data = get_all_data('almacen')
        
        # Obtener las fases actuales en el almacén
        fases_existentes = set()
        for item in almacen_data:
            if 'fase_actual' in item and item['fase_actual']:
                fase = str(item['fase_actual']).strip().upper()
                if fase in FASES_CAFE:
                    fases_existentes.add(fase)
        
        # Verificar si es necesario añadir fases faltantes
        fases_faltantes = set(FASES_CAFE) - fases_existentes
        if fases_faltantes:
            logger.info(f"Inicializando fases faltantes en almacén: {fases_faltantes}")
            
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for fase in fases_faltantes:
                # Añadir la fase con cantidad 0
                append_data('almacen', {
                    'id': generate_unique_id('AL'),
                    'compra_id': '',  # No hay compra asociada en la inicialización
                    'fecha': now,
                    'fase_actual': fase,
                    'cantidad_kg': 0,
                    'ultima_actualizacion': now,
                    'notas': 'Inicialización automática',
                    'registrado_por': 'sistema'
                })
            
            logger.info("Inicialización de fases en almacén completada")
        else:
            logger.info("Todas las fases ya están inicializadas en el almacén")
        
        return True
    except Exception as e:
        logger.error(f"Error al inicializar fases en almacén: {e}")
        return False

def generate_unique_id(prefix='CP', length=6):
    """
    Genera un ID único alfanumérico
    
    Args:
        prefix: Prefijo para el ID (default: 'CP' para compras, 'AL' para almacén)
        length: Longitud del ID (default: 6)
    
    Returns:
        str: ID único alfanumérico
    """
    # Caracteres permitidos (letras mayúsculas y números)
    chars = string.ascii_uppercase + string.digits
    
    # Generar un ID único con el prefijo especificado
    unique_id = prefix + '-' + ''.join(random.choice(chars) for _ in range(length))
    
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
        
        # Generar IDs únicos según el tipo de hoja
        if sheet_name == 'compras' and 'id' not in data:
            data['id'] = generate_unique_id('CP')
            logger.info(f"Generado ID único para compra: {data['id']}")
        elif sheet_name == 'almacen' and 'id' not in data:
            data['id'] = generate_unique_id('AL')
            logger.info(f"Generado ID único para almacén: {data['id']}")
        
        # Asegurarse de que tenemos la fecha actual
        if ('fecha' not in data or not data['fecha']) and sheet_name != 'compras':
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
                elif header in ['cantidad', 'precio', 'total', 'kg_disponibles', 'cantidad_kg', 'merma']:
                    data[header] = "0"
                elif header == 'fase_actual' and sheet_name == 'compras' and 'tipo_cafe' in data:
                    # Si es una compra, la fase inicial es el tipo de café
                    data[header] = data.get('tipo_cafe', "No especificado")
                elif header == 'ultima_actualizacion':
                    data[header] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        
        # ENFOQUE ROBUSTO CON MÚLTIPLES MÉTODOS DE RESPALDO
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
            
            # Si se agregó exitosamente una compra, actualizar también el almacén
            if sheet_name == 'compras' and 'tipo_cafe' in data and ('kg_disponibles' in data or 'cantidad' in data):
                try:
                    # Extraer fase y cantidad de la compra
                    fase = data['tipo_cafe']
                    cantidad = float(data.get('kg_disponibles', data.get('cantidad', 0)))
                    compra_id = data['id']
                    
                    # Registrar en el almacén
                    logger.info(f"Registrando en almacén la compra {compra_id} de {cantidad} kg de {fase}")
                    
                    # Crear entrada en el almacén
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    registro_almacen = {
                        'id': generate_unique_id('AL'),
                        'compra_id': compra_id,
                        'fecha': now,
                        'fase_actual': fase,
                        'cantidad_kg': cantidad,
                        'ultima_actualizacion': now,
                        'notas': f"Registro automático desde compra {compra_id}",
                        'registrado_por': data.get('registrado_por', 'sistema')
                    }
                    
                    # Registrar en el almacén
                    resultado_registro = append_data('almacen', registro_almacen)
                    
                    if resultado_registro:
                        logger.info(f"Registro en almacén exitoso para compra {compra_id}")
                    else:
                        logger.warning(f"Error al registrar en almacén la compra {compra_id}")
                except Exception as e:
                    logger.error(f"Error al registrar en almacén después de compra: {e}")
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
                    request_data = {
                        "values": [row_data]
                    }
                    
                    # Headers con token de autorización
                    headers = {
                        "Authorization": f"Bearer {service._http.credentials.token}",
                        "Content-Type": "application/json"
                    }
                    
                    # Realizar la solicitud POST
                    import requests
                    response = requests.post(url, json=request_data, headers=headers)
                    
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

def get_almacen_por_fase(fase):
    """
    Obtiene todos los registros del almacén para una fase específica
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, etc.)
        
    Returns:
        Lista de registros del almacén en la fase especificada
    """
    try:
        logger.info(f"Buscando registros en almacén para fase: {fase}")
        
        # Obtener registros filtrados por fase
        fase_normalizada = str(fase).strip().upper()
        registros = get_filtered_data('almacen', {'fase_actual': fase_normalizada})
        
        # Ordenar por fecha (más recientes primero)
        registros.sort(key=lambda x: x.get('fecha', ''), reverse=True)
        
        logger.info(f"Se encontraron {len(registros)} registros en almacén para fase {fase_normalizada}")
        return registros
    except Exception as e:
        logger.error(f"Error al obtener registros del almacén para fase {fase}: {e}")
        return []

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
        # Obtener todas las compras
        all_compras = get_all_data('compras')
        
        # Filtrar manualmente para evitar problemas de formato
        compras_disponibles = []
        for compra in all_compras:
            # Normalizar fase para comparación
            fase_actual = str(compra.get('fase_actual', '')).strip().upper()
            fase_buscada = str(fase).strip().upper()
            
            # Verificar si hay coincidencia de fase
            if fase_actual == fase_buscada:
                try:
                    # Verificar kg disponibles
                    kg_disponibles = float(str(compra.get('kg_disponibles', '0')).replace(',', '.'))
                    if kg_disponibles > 0:
                        # Agregar a la lista de compras disponibles
                        logger.info(f"Compra encontrada: {compra.get('proveedor')} - {kg_disponibles} kg - ID: {compra.get('id')}")
                        compras_disponibles.append(compra)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error al convertir kg_disponibles: {e}. Valor: {compra.get('kg_disponibles')}")
                    continue
        
        logger.info(f"Total compras encontradas en fase {fase}: {len(compras_disponibles)}")
        return compras_disponibles
    except Exception as e:
        logger.error(f"Error al obtener compras en fase {fase}: {e}")
        return []

def get_total_almacen_por_fase(fase):
    """
    Obtiene la cantidad total disponible en el almacén para una fase específica
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, etc.)
    
    Returns:
        float: Cantidad total disponible en kg
    """
    try:
        # Normalizar fase para búsqueda
        fase_buscada = fase.strip().upper()
        
        # Obtener registros del almacén para esta fase
        registros = get_almacen_por_fase(fase_buscada)
        
        if not registros:
            logger.warning(f"No se encontraron registros en el almacén para la fase {fase_buscada}")
            return 0.0
        
        # Sumar todas las cantidades
        total = 0.0
        for registro in registros:
            try:
                cantidad = float(str(registro.get('cantidad_kg', '0')).replace(',', '.'))
                total += cantidad
            except (ValueError, TypeError) as e:
                logger.warning(f"Error al convertir cantidad: {e}. Valor: {registro.get('cantidad_kg')}")
                continue
        
        logger.info(f"Total en almacén para fase {fase_buscada}: {total} kg")
        return total
    except Exception as e:
        logger.error(f"Error al obtener total en almacén para fase {fase}: {e}")
        return 0.0

def registrar_proceso(origen, destino, cantidad, merma=0, compras_ids=None, notas="", registrado_por=""):
    """
    Registra un proceso de transformación de café de una fase a otra
    
    Args:
        origen: Fase de origen
        destino: Fase de destino
        cantidad: Cantidad a procesar en kg
        merma: Cantidad de merma en kg (default: 0)
        compras_ids: Lista de IDs de compras relacionadas (default: None)
        notas: Notas adicionales sobre el proceso (default: "")
        registrado_por: Usuario que registra el proceso (default: "")
    
    Returns:
        bool: True si se registró correctamente, False en caso contrario
    """
    try:
        logger.info(f"Registrando proceso de {origen} a {destino} de {cantidad} kg (merma: {merma} kg)")
        
        # Verificar que la transición sea válida
        if not es_transicion_valida(origen, destino):
            logger.error(f"Transición inválida: {origen} -> {destino}")
            return False, f"Transición inválida: {origen} -> {destino}"
        
        # Verificar que hay suficiente cantidad disponible en el almacén
        total_disponible = get_total_almacen_por_fase(origen)
        if total_disponible < float(cantidad):
            logger.error(f"Cantidad insuficiente en almacén para fase {origen}: {total_disponible} kg disponibles, {cantidad} kg solicitados")
            return False, f"Cantidad insuficiente en almacén para fase {origen}: {total_disponible} kg disponibles, {cantidad} kg solicitados"
        
        # Preparar datos para el registro del proceso
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        proceso_data = {
            "fecha": now,
            "origen": origen,
            "destino": destino,
            "cantidad": cantidad,
            "compras_ids": compras_ids if compras_ids else "",
            "merma": merma,
            "notas": notas,
            "registrado_por": registrado_por
        }
        
        # Registrar el proceso
        proceso_registrado = append_data("proceso", proceso_data)
        
        if not proceso_registrado:
            logger.error("Error al registrar el proceso en la hoja 'proceso'")
            return False, "Error al registrar el proceso"
        
        # Crear registro para restar del almacén en la fase de origen
        resta_origen = {
            "id": generate_unique_id('AL'),
            "compra_id": "",  # No aplica en este caso
            "fecha": now,
            "fase_actual": origen,
            "cantidad_kg": -float(cantidad),  # Valor negativo para restar
            "ultima_actualizacion": now,
            "notas": f"Proceso a {destino}. Merma: {merma} kg.",
            "registrado_por": registrado_por
        }
        
        # Registrar la resta del origen
        resta_registrada = append_data("almacen", resta_origen)
        
        if not resta_registrada:
            logger.error(f"Error al registrar la resta en almacén para fase {origen}")
            return False, f"Error al registrar la resta en almacén para fase {origen}"
        
        # Calcular cantidad resultante (restando merma)
        cantidad_resultante = max(0, float(cantidad) - float(merma))
        
        # Crear registro para sumar al almacén en la fase de destino
        suma_destino = {
            "id": generate_unique_id('AL'),
            "compra_id": "",  # No aplica en este caso
            "fecha": now,
            "fase_actual": destino,
            "cantidad_kg": cantidad_resultante,
            "ultima_actualizacion": now,
            "notas": f"Procesado desde {origen}. Merma: {merma} kg.",
            "registrado_por": registrado_por
        }
        
        # Registrar la suma al destino
        suma_registrada = append_data("almacen", suma_destino)
        
        if not suma_registrada:
            logger.error(f"Error al registrar la suma en almacén para fase {destino}")
            return False, f"Error al registrar la suma en almacén para fase {destino}"
        
        logger.info(f"Proceso registrado correctamente: {origen} -> {destino}, {cantidad} kg, merma: {merma} kg")
        return True, "Proceso registrado correctamente"
    except Exception as e:
        logger.error(f"Error al registrar proceso: {e}")
        return False, f"Error al registrar proceso: {str(e)}"

def sincronizar_almacen_con_compras():
    """
    Sincroniza el almacén con las existencias actuales en las compras.
    Útil para inicializar o corregir discrepancias.
    
    Returns:
        bool: True si se sincronizó correctamente, False en caso contrario
    """
    try:
        logger.info("Iniciando sincronización de almacén con compras")
        
        # Para cada fase, obtener las compras disponibles
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        resultados = []
        
        for fase in FASES_CAFE:
            # Obtener compras disponibles para esta fase
            compras = get_compras_por_fase(fase)
            
            if compras:
                logger.info(f"Sincronizando fase {fase}: {len(compras)} compras encontradas")
                
                # Para cada compra, verificar si ya existe en el almacén
                for compra in compras:
                    compra_id = compra.get('id', '')
                    kg_disponibles = float(str(compra.get('kg_disponibles', '0')).replace(',', '.'))
                    
                    if kg_disponibles > 0 and compra_id:
                        # Verificar si esta compra ya está registrada en el almacén
                        registros_almacen = get_filtered_data('almacen', {'compra_id': compra_id})
                        
                        if not registros_almacen:
                            # No existe registro en el almacén para esta compra, crear uno
                            registro_almacen = {
                                'id': generate_unique_id('AL'),
                                'compra_id': compra_id,
                                'fecha': now,
                                'fase_actual': fase,
                                'cantidad_kg': kg_disponibles,
                                'ultima_actualizacion': now,
                                'notas': f"Sincronización automática desde compra {compra_id}",
                                'registrado_por': 'sistema_sincronizacion'
                            }
                            
                            resultado = append_data('almacen', registro_almacen)
                            resultados.append(resultado)
                            
                            if resultado:
                                logger.info(f"Registro creado en almacén para compra {compra_id} ({kg_disponibles} kg)")
                            else:
                                logger.error(f"Error al crear registro en almacén para compra {compra_id}")
                        else:
                            logger.info(f"Compra {compra_id} ya tiene registro en almacén")
            else:
                logger.info(f"No hay compras disponibles para fase {fase}")
        
        # Verificar resultados
        if all(resultados):
            logger.info("Sincronización de almacén completada exitosamente")
            return True
        elif not resultados:
            logger.info("No se requirieron actualizaciones al almacén")
            return True
        else:
            logger.warning(f"Sincronización parcial: {resultados.count(True)}/{len(resultados)} operaciones exitosas")
            return False
    except Exception as e:
        logger.error(f"Error al sincronizar almacén con compras: {e}")
        return False