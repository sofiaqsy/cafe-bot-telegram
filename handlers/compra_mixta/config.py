"""
Constantes y configuraciones para el módulo de compra mixta
"""
import logging

# Configurar logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def debug_log(message):
    """Función especial para logs de depuración más visibles"""
    logger.debug(f"### DEBUG ### {message}")
    # Agregar también como INFO para asegurar que se vea
    logger.info(f"### DEBUG ### {message}")

# Estados para la conversación
TIPO_CAFE, PROVEEDOR, CANTIDAD, PRECIO, METODO_PAGO, MONTO_EFECTIVO, MONTO_TRANSFERENCIA, MONTO_ADELANTO, MONTO_POR_PAGAR, SELECCIONAR_ADELANTO, CONFIRMAR = range(11)

# Tipos de café predefinidos - solo 3 opciones fijas
TIPOS_CAFE = ["CEREZO", "MOTE", "PERGAMINO"]

# Métodos de pago disponibles (actualizados con las nuevas combinaciones)
METODOS_PAGO = [
    "EFECTIVO", 
    "TRANSFERENCIA", 
    "EFECTIVO Y TRANSFERENCIA", 
    "ADELANTO", 
    "EFECTIVO Y ADELANTO", 
    "TRANSFERENCIA Y ADELANTO",
    "ADELANTO Y EFECTIVO",   # Nueva opción
    "ADELANTO Y TRANSFERENCIA",  # Nueva opción
    "ADELANTO Y POR PAGAR"   # Nueva opción
]

# Headers para la hoja de compras mixtas
COMPRAS_MIXTAS_HEADERS = [
    "id", "fecha", "tipo_cafe", "proveedor", "cantidad", "precio", "preciototal", 
    "metodo_pago", "monto_efectivo", "monto_transferencia", "monto_adelanto", 
    "monto_por_pagar", "adelanto_id", "registrado_por", "notas"
]

# Datos temporales de la compra
datos_compra_mixta = {}
