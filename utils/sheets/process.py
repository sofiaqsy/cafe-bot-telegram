"""
Módulo para gestionar los procesos de transformación del café en el sistema de hojas de cálculo.
"""
import logging

from utils.sheets.constants import TRANSICIONES_PERMITIDAS, MERMAS_SUGERIDAS
from utils.sheets.almacen import update_almacen

# Configurar logging
logger = logging.getLogger(__name__)

def es_transicion_valida(origen, destino):
    """
    Verifica si la transición de fase es válida.
    
    Args:
        origen: Fase de origen
        destino: Fase de destino
        
    Returns:
        bool: True si la transición es válida, False en caso contrario
    """
    if origen not in TRANSICIONES_PERMITIDAS:
        return False
    
    return destino in TRANSICIONES_PERMITIDAS[origen]

def calcular_merma_sugerida(origen, destino, cantidad):
    """
    Calcula la merma sugerida para una transición específica.
    
    Args:
        origen: Fase de origen
        destino: Fase de destino
        cantidad: Cantidad a procesar en kg
        
    Returns:
        float: Merma sugerida en kg
    """
    try:
        # Construir clave para buscar en el diccionario de mermas
        clave_merma = f"{origen}_{destino}"
        
        # Verificar si existe un porcentaje de merma para esta transición
        if clave_merma in MERMAS_SUGERIDAS:
            factor_merma = MERMAS_SUGERIDAS[clave_merma]
            merma_calculada = float(cantidad) * factor_merma
            return round(merma_calculada, 2)
        
        return 0.0
    except Exception as e:
        logger.error(f"Error al calcular merma sugerida: {e}")
        return 0.0

def actualizar_almacen_desde_proceso(origen, destino, cantidad, merma):
    """
    Actualiza el almacén basado en un proceso de transformación.
    
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
        
        # Manejar el caso donde resultado_origen es una tuple (usado en ventas)
        if isinstance(resultado_origen, tuple):
            resultado_origen = resultado_origen[0]
        
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