"""
Funciones utilitarias para el módulo de compra mixta.
"""
import traceback
from utils.sheets import get_all_data
from handlers.compra_mixta.config import debug_log

def obtener_proveedores_con_adelantos():
    """
    Obtiene una lista de proveedores que tienen adelantos con saldo disponible
    
    Returns:
        set: Conjunto de nombres de proveedores con adelantos disponibles
    """
    try:
        debug_log("INICIANDO obtener_proveedores_con_adelantos")
        # Obtener todos los adelantos, sin filtrar
        adelantos = get_all_data("adelantos")
        debug_log(f"Obtenidos {len(adelantos)} registros de adelantos en total")
        
        # Imprimir los primeros registros para depuración
        for i, adelanto in enumerate(adelantos[:3]):
            debug_log(f"Adelanto #{i}: {adelanto.get('proveedor')} - Saldo: {adelanto.get('saldo_restante')}")
        
        # Obtener proveedores únicos con saldo > 0
        proveedores_con_adelanto = set()
        for adelanto in adelantos:
            try:
                proveedor = adelanto.get('proveedor', '')
                if not proveedor:
                    continue
                    
                saldo_str = adelanto.get('saldo_restante', '0')
                debug_log(f"Procesando adelanto para {proveedor} con saldo_restante={saldo_str}")
                
                # Validar explícitamente el valor de saldo
                try:
                    saldo = 0
                    if saldo_str:
                        saldo = float(str(saldo_str).replace(',', '.'))
                except (ValueError, TypeError):
                    debug_log(f"Error al convertir saldo_restante: '{saldo_str}'")
                    saldo = 0
                
                if saldo > 0:
                    proveedores_con_adelanto.add(proveedor)
                    debug_log(f"Añadido proveedor {proveedor} con saldo {saldo}")
            except Exception as e:
                debug_log(f"Error procesando adelanto: {e} - Datos: {adelanto}")
                continue
        
        debug_log(f"Se encontraron {len(proveedores_con_adelanto)} proveedores con adelantos disponibles: {sorted(list(proveedores_con_adelanto))}")
        return proveedores_con_adelanto
    except Exception as e:
        debug_log(f"ERROR CRÍTICO en obtener_proveedores_con_adelantos: {e}")
        debug_log(traceback.format_exc())
        # En caso de error, devolver conjunto vacío para no interrumpir el flujo
        return set()
