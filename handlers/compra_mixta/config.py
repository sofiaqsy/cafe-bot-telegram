"""
Constantes y configuraciones para el módulo de compra mixta.
"""
import logging

# Configurar logging
logger = logging.getLogger(__name__)
# Asegurar que los logs sean visibles
logger.setLevel(logging.DEBUG)

# Estados para la conversación
TIPO_CAFE, PROVEEDOR, CANTIDAD, PRECIO, METODO_PAGO, MONTO_EFECTIVO, MONTO_TRANSFERENCIA, SELECCIONAR_ADELANTO, CONFIRMAR = range(9)

# Tipos de café predefinidos - solo 3 opciones fijas (copiado de compras.py)
TIPOS_CAFE = ["CEREZO", "MOTE", "PERGAMINO"]

# Métodos de pago disponibles
METODOS_PAGO = [
    "EFECTIVO", 
    "TRANSFERENCIA", 
    "EFECTIVO Y TRANSFERENCIA", 
    "ADELANTO", 
    "EFECTIVO Y ADELANTO", 
    "TRANSFERENCIA Y ADELANTO"
]

# Headers para la hoja de compras mixtas
COMPRAS_MIXTAS_HEADERS = [
    "id", "fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "preciototal", 
    "metodo_pago", "monto_efectivo", "monto_transferencia", "monto_adelanto", 
    "adelanto_id", "registrado_por", "notas"
]

# Datos temporales compartidos entre módulos
datos_compra_mixta = {}

def debug_log(message):
    """Función especial para logs de depuración más visibles"""
    logger.debug(f"### DEBUG ### {message}")
    # Agregar también como INFO para asegurar que se vea
    logger.info(f"### DEBUG ### {message}")
