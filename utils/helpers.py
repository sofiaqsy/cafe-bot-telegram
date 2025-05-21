import logging
import datetime
from decimal import Decimal
import pytz

# Configurar logging
logger = logging.getLogger(__name__)

# Importar el nuevo módulo de formateo
from utils.formatters import formatear_numero, formatear_precio, procesar_entrada_numerica

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
    """
    Formatea un valor como moneda
    
    NOTA: Esta función se mantiene para compatibilidad con el código existente.
    Para nuevas implementaciones, usar formatear_precio() del módulo formatters.
    """
    if not amount:
        return f"{symbol} 0,00"
    
    try:
        # Convertir a Decimal para precisión
        amount_dec = Decimal(str(amount))
        
        # Formatear con coma como separador decimal y punto como separador de miles
        amount_str = formatear_numero(amount_dec)
        formatted = f"{symbol} {amount_str}"
        return formatted
    except:
        return f"{symbol} {amount}"

def calculate_total(cantidad, precio):
    """Calcula el total (cantidad * precio)"""
    try:
        # Asegurar que ambos son números
        cantidad_float = procesar_entrada_numerica(str(cantidad))
        precio_float = procesar_entrada_numerica(str(precio))
        return cantidad_float * precio_float
    except (ValueError, TypeError) as e:
        logger.warning(f"Error al calcular total: {e}")
        return 0

def safe_float(text):
    """
    Convierte un texto a número float, manejando comas como separador decimal.
    
    NOTA: Esta función se mantiene para compatibilidad con el código existente.
    Para nuevas implementaciones, usar procesar_entrada_numerica() del módulo formatters.
    
    Args:
        text: Texto a convertir a float
        
    Returns:
        float: Valor convertido, o 0.0 si hay error
    """
    if not text:
        return 0.0
    try:
        # Delegar a la nueva función
        return procesar_entrada_numerica(str(text))
    except (ValueError, TypeError) as e:
        logger.warning(f"Error al convertir '{text}' a float: {e}")
        return 0.0