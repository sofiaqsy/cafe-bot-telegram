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
    "compras": ["id", "fecha", "proveedor", "tipo_cafe", "fase_actual", "cantidad", "kg_disponibles", "precio", "total", "notas", "registrado_por"],
    "proceso": ["fecha", "origen", "destino", "cantidad", "compras_ids", "merma", "notas", "registrado_por"],
    "gastos": ["fecha", "categoria", "monto", "descripcion", "registrado_por"],
    "ventas": ["fecha", "cliente", "tipo_cafe", "peso", "precio_kg", "total", "notas", "registrado_por"],
    "pedidos": ["fecha", "cliente", "tipo_cafe", "cantidad", "precio_kg", "total", "estado", "fecha_entrega", "notas", "registrado_por"],
    "adelantos": ["fecha", "hora", "cliente", "monto", "notas", "registrado_por"],
    "almacen": ["fase", "cantidad", "ultima_actualizacion", "notas"]
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
                            'fase': fase,
                            'cantidad': 0,
                            'ultima_actualizacion': now,
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
        sheets = get_sheet_service()
        
        # Para compras, asegurar que tenga un ID único
        if sheet_name == 'compras' and 'id' not in data:
            data['id'] = generate_unique_id()
            logger.info(f"Generado ID único para compra: {data['id']}")
        
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
        
        # Usar el enfoque manual: obtener el número de filas actuales y añadir en la siguiente fila
        # Este método evita el uso de append() que está causando problemas
        try:
            # Primero, contar cuántas filas hay actualmente 
            range_name = f"{sheet_name}!A:A"
            response = sheets.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            # Determinar la próxima fila a usar (filas actuales + 1)
            values = response.get('values', [])
            next_row = len(values) + 1
            logger.info(f"Se añadirán datos en la fila {next_row}")
            
            # Construir el rango que abarcará todos los datos
            update_range = f"{sheet_name}!A{next_row}"
            
            # Escribir los datos directamente
            sheets.values().update(
                spreadsheetId=spreadsheet_id,
                range=update_range,
                valueInputOption="USER_ENTERED",
                body={"values": [row_data]}
            ).execute()
            
            logger.info(f"Datos añadidos correctamente a '{sheet_name}' en la fila {next_row}")
            return True
        except Exception as e:
            logger.error(f"Error al añadir datos: {e}")
            # Si falla el método manual, intentar otro enfoque
            try:
                logger.info("Intentando método alternativo de añadir al final...")
                
                # Calcular un rango muy grande que abarque toda la hoja
                # Esto es menos eficiente pero puede funcionar como último recurso
                all_data_range = f"{sheet_name}!A1:Z1000"
                response = sheets.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=all_data_range
                ).execute()
                
                # Determinar la próxima fila a usar
                all_values = response.get('values', [])
                next_row = len(all_values) + 1
                
                # Construir un rango específico para esta fila
                final_range = f"{sheet_name}!A{next_row}:Z{next_row}"
                
                # Hacer la actualización
                sheets.values().update(
                    spreadsheetId=spreadsheet_id,
                    range=final_range,
                    valueInputOption="USER_ENTERED",
                    body={"values": [row_data]}
                ).execute()
                
                logger.info(f"Datos añadidos con método alternativo a '{sheet_name}' en la fila {next_row}")
                return True
            except Exception as alt_e:
                logger.error(f"Error total al añadir datos: {alt_e}")
                return False
    except Exception as e:
        logger.error(f"Error global al añadir datos a {sheet_name}: {e}")
        return False