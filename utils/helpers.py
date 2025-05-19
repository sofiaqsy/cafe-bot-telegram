import string
import random
import logging

# Configurar logging
logger = logging.getLogger(__name__)

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