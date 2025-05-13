"""
Funciones de ayuda para el bot de café
"""
import datetime
import pytz

def get_now_peru():
    """
    Obtiene la fecha y hora actuales en la zona horaria de Perú
    """
    tz_peru = pytz.timezone('America/Lima')
    return datetime.datetime.now(tz_peru)

def format_currency(amount):
    """
    Formatea un valor monetario
    """
    return f"S/ {float(amount):.2f}"

def calculate_total(cantidad, precio):
    """
    Calcula el precio total
    """
    return float(cantidad) * float(precio)

def format_datetime(dt):
    """
    Formatea una fecha y hora
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_current_timestamp():
    """
    Obtiene un timestamp actual
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")