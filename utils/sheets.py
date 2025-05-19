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

def initialize_sheets():
    """Inicializa las hojas de Google Sheets con las cabeceras correctas"""
    global _sheets_initialized
    
    # Si ya se inicializaron las hojas en esta sesión, no volver a hacerlo
    if _sheets_initialized:
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
                            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        _sheets_initialized = True
        
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
                data['fecha'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Agregar fecha de actualización si no existe
            if 'fecha_actualizacion' not in data or not data['fecha_actualizacion']:
                data['fecha_actualizacion'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            
            # CAMBIO: Ya no se crea un registro en almacén al ejecutar un proceso de /compra
            # Solo se actualiza cantidad_actual si existe un registro correspondiente en almacén
            if sheet_name == 'compras' and 'tipo_cafe' in data and 'cantidad' in data:
                try:
                    # Extraer datos de la compra
                    fase = data['tipo_cafe']
                    cantidad = float(str(data.get('cantidad', '0')).replace(',', '.'))
                    compra_id = data.get('id', '')
                    
                    # Buscar registro existente de almacén para actualizar la cantidad
                    registros_almacen = get_filtered_data('almacen', {'fase_actual': fase})
                    
                    if registros_almacen:
                        # Actualizar la cantidad del registro de almacén existente
                        registro_almacen = registros_almacen[0]
                        cantidad_actual = safe_float(registro_almacen.get('cantidad_actual', 0))
                        nueva_cantidad = cantidad_actual - cantidad
                        
                        if nueva_cantidad < 0:
                            nueva_cantidad = 0
                            logger.warning(f"Cantidad resultante negativa, estableciendo a 0 para fase: {fase}")
                        
                        # Actualizar el registro
                        row_index = registro_almacen.get('_row_index')
                        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Actualizar cantidad_actual
                        update_cell('almacen', row_index, 'cantidad_actual', str(nueva_cantidad))
                        
                        # Actualizar fecha de actualización
                        update_cell('almacen', row_index, 'fecha_actualizacion', now)
                        
                        # Actualizar notas para incluir la operación
                        notas_actuales = registro_almacen.get('notas', '')
                        nuevas_notas = f"{notas_actuales}; {now}: Compra {compra_id} - Restado {cantidad} kg."
                        update_cell('almacen', row_index, 'notas', nuevas_notas)
                        
                        logger.info(f"Actualizado registro de almacén para fase {fase}: cantidad_actual = {nueva_cantidad}")
                    else:
                        logger.warning(f"No se encontró registro en almacén para la fase {fase}, no se actualizó ninguna cantidad")
                    
                except Exception as e:
                    logger.error(f"Error al actualizar cantidad en almacén para compra: {e}")
                    # No fallar si hay un error en el almacén, solo registrar
            
            return True