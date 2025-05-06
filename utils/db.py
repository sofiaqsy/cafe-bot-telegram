import csv
import os
from typing import List, Dict, Any

def ensure_file_exists(filename: str, headers: List[str]) -> None:
    """
    Asegura que el archivo CSV existe. Si no existe, lo crea con los encabezados.
    
    Args:
        filename: Ruta del archivo
        headers: Lista de encabezados para el CSV
    """
    # Verificar si el directorio existe
    directory = os.path.dirname(filename)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    
    # Verificar si el archivo existe, si no, crearlo con encabezados
    if not os.path.exists(filename):
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

def read_data(filename: str) -> List[Dict[str, Any]]:
    """
    Lee los datos de un archivo CSV y los devuelve como una lista de diccionarios.
    
    Args:
        filename: Ruta del archivo CSV
        
    Returns:
        Lista de diccionarios con los datos del CSV
    """
    if not os.path.exists(filename):
        return []
    
    with open(filename, 'r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        data = list(reader)
    
    return data

def write_data(filename: str, data: List[Dict[str, Any]], headers: List[str]) -> None:
    """
    Escribe datos en un archivo CSV.
    
    Args:
        filename: Ruta del archivo CSV
        data: Lista de diccionarios con los datos a escribir
        headers: Lista de encabezados para el CSV
    """
    ensure_file_exists(filename, headers)
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def append_data(filename: str, row: Dict[str, Any], headers: List[str]) -> None:
    """
    Añade una fila de datos al final de un archivo CSV.
    
    Args:
        filename: Ruta del archivo CSV
        row: Diccionario con los datos a añadir
        headers: Lista de encabezados para el CSV
    """
    ensure_file_exists(filename, headers)
    
    with open(filename, 'a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writerow(row)
