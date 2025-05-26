"""
Módulo con funciones utilitarias para el sistema de hojas de cálculo.
"""
import logging
import string
import random
import datetime

# Configurar logging
logger = logging.getLogger(__name__)

def generate_unique_id(prefix="CP-", length=6):
    """
    Genera un ID único alfanumérico
    
    Args:
        prefix: Prefijo para el ID (default: "CP-" para compras)
        length: Longitud del ID (default: 6)
    
    Returns:
        str: ID único alfanumérico
    """
    # Caracteres permitidos (letras mayúsculas y números)
    chars = string.ascii_uppercase + string.digits
    
    # Generar un ID único
    unique_id = prefix + ''.join(random.choice(chars) for _ in range(length))
    
    return unique_id

def generate_almacen_id(length=6):
    """
    Genera un ID único alfanumérico para registros del almacén
    
    Args:
        length: Longitud del ID (default: 6)
    
    Returns:
        str: ID único alfanumérico
    """
    return generate_unique_id("AL-", length)

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

def get_current_datetime_str():
    """
    Obtiene la fecha y hora actual como string formateado
    
    Returns:
        str: Fecha y hora actual en formato YYYY-MM-DD HH:MM:SS
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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