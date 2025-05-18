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
                result = sheets.values().update(
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
        if (sheet_name == 'adelantos' and column_name == 'fecha') or column_name == 'fecha':
            value = format_date_for_sheets(value)
        
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
        
        # Obtener datos de almacén filtrados por fase
        almacen_data = get_filtered_data('almacen', {'fase': fase_buscada})
        
        if not almacen_data:
            logger.warning(f"No se encontró la fase {fase_buscada} en el almacén")
            return 0.0
        
        # Tomar el primer registro que coincida
        registro = almacen_data[0]
        
        # Convertir cantidad a float
        try:
            cantidad = float(str(registro.get('cantidad', '0')).replace(',', '.'))
            logger.info(f"Cantidad en almacén para fase {fase_buscada}: {cantidad} kg")
            return cantidad
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir cantidad en almacén: {e}")
            return 0.0
    except Exception as e:
        logger.error(f"Error al obtener cantidad en almacén para fase {fase}: {e}")
        return 0.0

def update_almacen(fase, cantidad_cambio, operacion="sumar", notas=""):
    """
    Actualiza la cantidad disponible en el almacén para una fase específica
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, etc.)
        cantidad_cambio: Cantidad a sumar o restar
        operacion: "sumar" para añadir, "restar" para disminuir, "establecer" para fijar valor
        notas: Notas adicionales sobre la operación
    
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        import datetime
        
        logger.info(f"Actualizando almacén - Fase: {fase}, Cambio: {cantidad_cambio} kg, Operación: {operacion}")
        
        # Normalizar fase
        fase_normalizada = fase.strip().upper()
        
        # Obtener datos actuales del almacén para esta fase
        almacen_data = get_filtered_data('almacen', {'fase': fase_normalizada})
        
        # Si no existe la fase, verificar si es válida y añadirla
        if not almacen_data:
            if fase_normalizada in FASES_CAFE:
                logger.info(f"Fase {fase_normalizada} no encontrada en almacén. Creando...")
                
                # Crear nuevo registro para esta fase
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cantidad_final = cantidad_cambio if operacion in ["sumar", "establecer"] else 0
                
                nueva_entrada = {
                    "fase": fase_normalizada,
                    "cantidad": cantidad_final,
                    "ultima_actualizacion": now,
                    "notas": f"Fase creada. {notas}"
                }
                
                # Añadir a la hoja
                return append_data("almacen", nueva_entrada)
            else:
                logger.error(f"Fase {fase_normalizada} no válida para almacén")
                return False
        
        # Obtener registro y su índice
        registro = almacen_data[0]
        row_index = registro.get('_row_index')
        
        # Convertir cantidad actual a float
        try:
            cantidad_actual = float(str(registro.get('cantidad', '0')).replace(',', '.'))
        except (ValueError, TypeError):
            logger.warning(f"Cantidad actual no válida: {registro.get('cantidad')}. Usando 0.")
            cantidad_actual = 0.0
        
        # Calcular nueva cantidad según la operación
        if operacion == "sumar":
            nueva_cantidad = cantidad_actual + float(cantidad_cambio)
        elif operacion == "restar":
            nueva_cantidad = max(0, cantidad_actual - float(cantidad_cambio))  # Nunca menor que 0
        elif operacion == "establecer":
            nueva_cantidad = max(0, float(cantidad_cambio))  # Nunca menor que 0
        else:
            logger.error(f"Operación no válida: {operacion}")
            return False
        
        # Redondear a 2 decimales
        nueva_cantidad = round(nueva_cantidad, 2)
        
        # Actualizar campos
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Actualizar cantidad
        update_cell("almacen", row_index, "cantidad", nueva_cantidad)
        
        # Actualizar fecha
        update_cell("almacen", row_index, "ultima_actualizacion", now)
        
        # Actualizar notas (añadir a las existentes)
        notas_actuales = registro.get('notas', '')
        nuevas_notas = f"{notas_actuales}; {now}: {operacion.capitalize()} {cantidad_cambio} kg - {notas}"[:250]  # Limitar longitud
        update_cell("almacen", row_index, "notas", nuevas_notas)
        
        logger.info(f"Almacén actualizado - Fase: {fase_normalizada}, Nueva cantidad: {nueva_cantidad} kg")
        return True
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
        
        # Para cada fase, calcular la suma total de kg disponibles
        totales_por_fase = {}
        for fase in FASES_CAFE:
            compras = get_compras_por_fase(fase)
            total_kg = sum(float(str(compra.get('kg_disponibles', '0')).replace(',', '.')) for compra in compras)
            totales_por_fase[fase] = round(total_kg, 2)
            logger.info(f"Fase {fase}: {total_kg} kg disponibles en compras")
        
        # Actualizar cada fase en el almacén
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for fase, total in totales_por_fase.items():
            update_almacen(
                fase=fase,
                cantidad_cambio=total,
                operacion="establecer",
                notas=f"Sincronización automática con compras ({now})"
            )
        
        logger.info("Sincronización de almacén completada")
        return True
    except Exception as e:
        logger.error(f"Error al sincronizar almacén: {e}")
        return False