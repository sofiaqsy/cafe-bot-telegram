import csv
import os
import datetime
import logging
from typing import List, Dict, Any
from utils.sheets import append_data as sheets_append_data
from utils.sheets import get_all_data, get_filtered_data, initialize_sheets

# Configurar logging
logger = logging.getLogger(__name__)

def ensure_file_exists(filename: str, headers: List[str]) -> None:
    """
    Asegura que el archivo CSV existe. Si no existe, lo crea con los encabezados.
    Se mantiene para compatibilidad con código existente, pero ahora usa Google Sheets.
    
    Args:
        filename: Ruta del archivo (ya no se usa directamente)
        headers: Lista de encabezados para el CSV
    """
    # Obtener el nombre de la hoja del nombre del archivo
    sheet_name = os.path.splitext(os.path.basename(filename))[0]
    logger.info(f"Asegurando que la hoja '{sheet_name}' existe con encabezados: {headers}")
    
    # Inicializar las hojas de Google Sheets
    initialize_sheets()

def read_data(filename: str) -> List[Dict[str, Any]]:
    """
    Lee los datos desde Google Sheets.
    
    Args:
        filename: Ruta del archivo original (se usa para identificar la hoja)
        
    Returns:
        Lista de diccionarios con los datos
    """
    # Obtener el nombre de la hoja del nombre del archivo
    sheet_name = os.path.splitext(os.path.basename(filename))[0]
    logger.info(f"Leyendo datos de la hoja '{sheet_name}'")
    
    # Leer datos de Google Sheets
    data = get_all_data(sheet_name)
    logger.info(f"Leídos {len(data)} registros de la hoja '{sheet_name}'")
    return data

def write_data(filename: str, data: List[Dict[str, Any]], headers: List[str]) -> None:
    """
    Escribe datos en Google Sheets.
    
    Args:
        filename: Ruta del archivo original (se usa para identificar la hoja)
        data: Lista de diccionarios con los datos a escribir
        headers: Lista de encabezados (ya no se usa directamente)
    """
    # Esta función no se implementa directamente para Google Sheets
    # En su lugar, usaríamos append_data para cada fila
    # O implementaríamos una función que borra todos los datos y los reescribe
    
    # Por ahora, imprimimos un mensaje de advertencia
    logger.warning("write_data no está completamente implementado para Google Sheets")
    logger.warning("Para actualizar todos los datos, considera una implementación personalizada")

def append_data(filename: str, row: Dict[str, Any], headers: List[str]) -> bool:
    """
    Añade una fila de datos a Google Sheets.
    
    Args:
        filename: Ruta del archivo original (se usa para identificar la hoja)
        row: Diccionario con los datos a añadir
        headers: Lista de encabezados para verificar campos requeridos
    
    Returns:
        bool: True si se guardaron los datos correctamente, False en caso contrario
    """
    # Obtener el nombre de la hoja del nombre del archivo
    sheet_name = os.path.splitext(os.path.basename(filename))[0]
    logger.info(f"Añadiendo datos a la hoja '{sheet_name}': {row}")
    
    # Verificar que todos los campos requeridos estén presentes
    campos_faltantes = [campo for campo in headers if campo not in row or not row.get(campo)]
    if campos_faltantes:
        logger.warning(f"Campos faltantes en los datos: {campos_faltantes}. Se usarán valores por defecto.")
    
    # Asegurarse de que la fila tiene una fecha (si no existe)
    if 'fecha' not in row or not row['fecha']:
        row['fecha'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Añadida fecha automática: {row['fecha']}")
    
    # Asegurarse de que todos los campos requeridos tengan al menos un valor por defecto
    for campo in headers:
        if campo not in row or not row[campo]:
            if campo == 'tipo_cafe':
                row[campo] = "No especificado"
                logger.info(f"Añadido valor por defecto para {campo}: {row[campo]}")
            elif campo in ['cantidad', 'precio', 'total']:
                row[campo] = "0"
                logger.info(f"Añadido valor por defecto para {campo}: {row[campo]}")
            else:
                row[campo] = ""
                logger.info(f"Añadido valor vacío para {campo}")
    
    # Añadir la fila a Google Sheets
    try:
        # Llamar a la función con el nombre de la hoja y los datos
        result = sheets_append_data(sheet_name, row)
        
        if result:
            logger.info(f"Datos añadidos correctamente a la hoja '{sheet_name}'")
            return True
        else:
            logger.error(f"Error al añadir datos a la hoja '{sheet_name}'")
            return False
    except Exception as e:
        logger.error(f"Error al añadir datos a la hoja '{sheet_name}': {e}")
        raise