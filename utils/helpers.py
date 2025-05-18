import logging
import datetime
from decimal import Decimal
import pytz

# Configurar logging
logger = logging.getLogger(__name__)

def get_now_peru():
    """Obtiene la fecha y hora actual en la zona horaria de Perú"""
    peru_tz = pytz.timezone('America/Lima')
    return datetime.datetime.now(peru_tz)

def format_date_for_sheets(date_string):
    """
    Formatea una cadena de fecha para evitar la conversión automática en Google Sheets.
    
    Args:
        date_string: Cadena de texto con la fecha
        
    Returns:
        str: Fecha con un apóstrofe al inicio para forzar el formato de texto en Google Sheets
    """
    if not date_string:
        return ""
    
    # Añadir un apóstrofe al inicio para forzar el formato de texto en Google Sheets
    return f"'{date_string}"

def format_currency(amount, symbol="S/"):
    """Formatea un valor como moneda"""
    if not amount:
        return f"{symbol} 0.00"
    
    try:
        # Convertir a Decimal para precisión
        amount_dec = Decimal(str(amount))
        
        # Formatear a 2 decimales
        formatted = f"{symbol} {amount_dec:.2f}"
        return formatted
    except:
        return f"{symbol} {amount}"

def calculate_total(cantidad, precio):
    """Calcula el total (cantidad * precio)"""
    try:
        return float(cantidad) * float(precio)
    except (ValueError, TypeError):
        return 0

def safe_float(text):
    """
    Convierte un texto a número float, manejando comas como separador decimal.
    
    Args:
        text: Texto a convertir a float
        
    Returns:
        float: Valor convertido, o 0.0 si hay error
    """
    if not text:
        return 0.0
    try:
        # Reemplazar comas por puntos para la conversión
        return float(str(text).replace(',', '.').strip())
    except (ValueError, TypeError):
        logger.warning(f"Error al convertir '{text}' a float, retornando 0.0")
        return 0.0