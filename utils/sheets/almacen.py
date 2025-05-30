"""
Módulo para gestionar el almacén de café en el sistema de hojas de cálculo.
"""
import logging
from typing import Tuple, Union, List, Dict, Any

from utils.sheets.constants import FASES_CAFE
from utils.sheets.core import get_filtered_data, append_data, update_cell, get_all_data
from utils.sheets.utils import safe_float, generate_almacen_id, get_current_datetime_str

# Configurar logging
logger = logging.getLogger(__name__)

def get_compras_por_fase(fase):
    """
    Obtiene todas las compras en una fase específica con kg disponibles.
    
    Args:
        fase: Fase actual del café (CEREZO, MOTE, PERGAMINO, VERDE)
        
    Returns:
        List[Dict]: Lista de compras en la fase especificada que aún tienen kg disponibles
    """
    try:
        logger.info(f"Buscando compras en fase: {fase}")
        
        # Buscar en almacén los registros con la fase actual especificada
        almacen_data = get_filtered_data('almacen', {'fase_actual': fase})
        
        if not almacen_data:
            logger.warning(f"No se encontró la fase {fase} en el almacén")
            return []
        
        # Filtrar solo aquellos que tienen kg disponibles
        almacen_con_disponible = []
        for registro in almacen_data:
            try:
                kg_disponibles = safe_float(registro.get('cantidad_actual', '0'))
                if kg_disponibles > 0:
                    almacen_con_disponible.append(registro)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error al convertir cantidad_actual: {e}. Valor: {registro.get('cantidad_actual')}")
        
        if not almacen_con_disponible:
            logger.warning(f"No hay registros en almacén con kg disponibles para la fase {fase}")
            return []
        
        # Obtener las compras correspondientes
        all_compras = get_all_data('compras')
        compras_disponibles = []
        
        for registro_almacen in almacen_con_disponible:
            compra_id = registro_almacen.get('compra_id', '')
            if not compra_id:
                continue
            
            # Buscar la compra correspondiente
            for compra in all_compras:
                if compra.get('id') == compra_id:
                    # Añadir kg_disponibles del almacén a la compra
                    compra_con_disponible = compra.copy()
                    compra_con_disponible['cantidad_actual'] = registro_almacen.get('cantidad_actual', '0')
                    compra_con_disponible['almacen_registro_id'] = registro_almacen.get('id', '')
                    compra_con_disponible['almacen_row_index'] = registro_almacen.get('_row_index', 0)
                    compras_disponibles.append(compra_con_disponible)
                    break
        
        logger.info(f"Total compras encontradas en fase {fase}: {len(compras_disponibles)}")
        return compras_disponibles
    except Exception as e:
        logger.error(f"Error al obtener compras en fase {fase}: {e}")
        return []

def get_almacen_cantidad(fase):
    """
    Obtiene la cantidad disponible de una fase específica del almacén.
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, VERDE)
    
    Returns:
        float: Cantidad disponible en kg
    """
    try:
        # Normalizar fase para búsqueda
        fase_buscada = fase.strip().upper()
        
        # Obtener datos de almacén filtrados por fase_actual
        almacen_data = get_filtered_data('almacen', {'fase_actual': fase_buscada})
        
        if not almacen_data:
            logger.warning(f"No se encontró la fase {fase_buscada} en el almacén")
            return 0.0
        
        # Calcular la suma total de kg disponibles
        total_disponible = 0.0
        for registro in almacen_data:
            try:
                kg_disponibles = safe_float(registro.get('cantidad_actual', '0'))
                total_disponible += kg_disponibles
            except (ValueError, TypeError) as e:
                logger.error(f"Error al convertir cantidad_actual: {e}")
        
        logger.info(f"Cantidad total en almacén para fase {fase_buscada}: {total_disponible} kg")
        return total_disponible
    except Exception as e:
        logger.error(f"Error al obtener cantidad en almacén para fase {fase}: {e}")
        return 0.0

def update_almacen_tostado(fase, cantidad_cambio, notas=""):
    """
    Actualiza la cantidad de café tostado disponible en el almacén (solo restar).
    Esta función modificará el registro existente en lugar de crear uno nuevo.
    
    Args:
        fase: Fase del café (TOSTADO)
        cantidad_cambio: Cantidad a restar
        notas: Notas adicionales sobre la operación
    
    Returns:
        Tuple[bool, str]: True si se actualizó correctamente y el ID del registro, o 
                          False y cadena vacía en caso contrario
    """
    try:
        if fase.strip().upper() != "TOSTADO":
            logger.error(f"Esta función solo es para actualizar café TOSTADO, se recibió: {fase}")
            return False, ""
            
        logger.info(f"Actualizando almacén TOSTADO - Cantidad a restar: {cantidad_cambio} kg")
        
        # Obtener todos los registros de TOSTADO con cantidad disponible
        almacen_data = get_filtered_data('almacen', {'fase_actual': 'TOSTADO'})
        
        if not almacen_data:
            logger.warning("No se encontraron registros de TOSTADO en el almacén")
            return False, ""
        
        # Filtrar los que tienen cantidad disponible
        registros_con_disponible = []
        for registro in almacen_data:
            try:
                kg_disponibles = safe_float(registro.get('cantidad_actual', '0'))
                if kg_disponibles > 0:
                    registros_con_disponible.append(registro)
            except (ValueError, TypeError) as e:
                logger.warning(f"Error al convertir cantidad_actual: {e}")
        
        if not registros_con_disponible:
            logger.warning("No hay suficiente café TOSTADO disponible en el almacén")
            return False, ""
        
        # Ordenar los registros por fecha (primero los más antiguos)
        registros_con_disponible.sort(key=lambda x: x.get('fecha', ''))
        
        # Cantidad restante por actualizar
        cantidad_restante = float(cantidad_cambio)
        resultados = []
        registro_usado = None
        
        for registro in registros_con_disponible:
            if cantidad_restante <= 0:
                break
                
            try:
                kg_disponibles = safe_float(registro.get('cantidad_actual', '0'))
                
                # Determinar cuánto restar de este registro
                cantidad_a_restar = min(kg_disponibles, cantidad_restante)
                nueva_cantidad = kg_disponibles - cantidad_a_restar
                
                # Actualizar en la hoja
                row_index = registro.get('_row_index')
                now = get_current_datetime_str()
                
                # Actualizar la celda de cantidad_actual
                result1 = update_cell('almacen', row_index, 'cantidad_actual', str(nueva_cantidad))
                
                # Actualizar la fecha de actualización
                result2 = update_cell('almacen', row_index, 'fecha_actualizacion', now)
                
                # Actualizar las notas para incluir esta operación
                notas_actuales = registro.get('notas', '')
                nuevas_notas = f"{notas_actuales}; {now}: Venta de {cantidad_a_restar} kg. {notas}"
                result3 = update_cell('almacen', row_index, 'notas', nuevas_notas)
                
                resultados.extend([result1, result2, result3])
                
                logger.info(f"Actualizado registro {registro.get('id')}: restado {cantidad_a_restar} kg, nuevo valor: {nueva_cantidad} kg")
                
                # Guardar el registro usado para relación en ventas
                if registro_usado is None:
                    registro_usado = registro
                
                # Actualizar cantidad restante
                cantidad_restante -= cantidad_a_restar
                
            except Exception as e:
                logger.error(f"Error al actualizar registro {registro.get('id')}: {e}")
        
        # Verificar si se pudo restar toda la cantidad solicitada
        if cantidad_restante > 0:
            logger.warning(f"No se pudo restar toda la cantidad solicitada. Faltan {cantidad_restante} kg")
            return False, ""
        
        # Verificar que todas las actualizaciones fueron exitosas
        almacen_id = registro_usado.get('id', '') if registro_usado else ""
        return all(resultados), almacen_id
        
    except Exception as e:
        logger.error(f"Error al actualizar almacén de TOSTADO: {e}")
        return False, ""

def update_almacen(fase, cantidad_cambio, operacion="sumar", notas="", compra_id=""):
    """
    Actualiza la cantidad disponible en el almacén para una fase específica.
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, VERDE, TOSTADO)
        cantidad_cambio: Cantidad a sumar o restar
        operacion: "sumar" para añadir, "restar" para disminuir, "establecer" para fijar valor
        notas: Notas adicionales sobre la operación
        compra_id: ID de compra relacionada (si aplica)
    
    Returns:
        Union[bool, Tuple[bool, str]]: 
            - Si es una venta: Tuple con bool que indica si se actualizó correctamente,
              y str que es el ID del almacén usado
            - En otros casos: bool que indica si se actualizó correctamente
    """
    try:
        logger.info(f"Actualizando almacén - Fase: {fase}, Cambio: {cantidad_cambio} kg, Operación: {operacion}, Compra ID: {compra_id}")
        
        # Normalizar fase
        fase_normalizada = fase.strip().upper()
        
        # Si la operación es "restar", actualizar registros existentes en lugar de crear uno nuevo con valor negativo
        if operacion == "restar":
            logger.info(f"Operación RESTAR en almacén para {fase_normalizada} - Cantidad: {cantidad_cambio} kg")
            
            # Obtener todos los registros con la fase actual y cantidad disponible
            almacen_data = get_filtered_data('almacen', {'fase_actual': fase_normalizada})
            
            if not almacen_data:
                logger.warning(f"No se encontraron registros de {fase_normalizada} en el almacén")
                return False, ""
            
            # Filtrar los que tienen cantidad disponible
            registros_con_disponible = []
            for registro in almacen_data:
                try:
                    kg_disponibles = safe_float(registro.get('cantidad_actual', '0'))
                    if kg_disponibles > 0:
                        registros_con_disponible.append(registro)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error al convertir cantidad_actual: {e}")
            
            if not registros_con_disponible:
                logger.warning(f"No hay suficiente café {fase_normalizada} disponible en el almacén")
                return False, ""
            
            # Ordenar los registros por fecha (primero los más antiguos)
            registros_con_disponible.sort(key=lambda x: x.get('fecha', ''))
            
            # Cantidad restante por actualizar
            cantidad_restante = float(cantidad_cambio)
            resultados = []
            registro_usado = None
            
            for registro in registros_con_disponible:
                if cantidad_restante <= 0:
                    break
                    
                try:
                    kg_disponibles = safe_float(registro.get('cantidad_actual', '0'))
                    
                    # Determinar cuánto restar de este registro
                    cantidad_a_restar = min(kg_disponibles, cantidad_restante)
                    nueva_cantidad = kg_disponibles - cantidad_a_restar
                    
                    # Actualizar en la hoja
                    row_index = registro.get('_row_index')
                    now = get_current_datetime_str()
                    
                    # Actualizar la celda de cantidad_actual
                    result1 = update_cell('almacen', row_index, 'cantidad_actual', str(nueva_cantidad))
                    
                    # Actualizar la fecha de actualización
                    result2 = update_cell('almacen', row_index, 'fecha_actualizacion', now)
                    
                    # Actualizar las notas para incluir esta operación
                    notas_actuales = registro.get('notas', '')
                    nuevas_notas = f"{notas_actuales}; {now}: {notas}"
                    result3 = update_cell('almacen', row_index, 'notas', nuevas_notas)
                    
                    resultados.extend([result1, result2, result3])
                    
                    logger.info(f"Actualizado registro {registro.get('id')}: restado {cantidad_a_restar} kg, nuevo valor: {nueva_cantidad} kg")
                    
                    # Guardar el registro usado para relación en ventas
                    if registro_usado is None:
                        registro_usado = registro
                    
                    # Actualizar cantidad restante
                    cantidad_restante -= cantidad_a_restar
                    
                except Exception as e:
                    logger.error(f"Error al actualizar registro {registro.get('id')}: {e}")
            
            # Verificar si se pudo restar toda la cantidad solicitada
            if cantidad_restante > 0:
                logger.warning(f"No se pudo restar toda la cantidad solicitada. Faltan {cantidad_restante} kg")
                return False, ""
            
            # Verificar que todas las actualizaciones fueron exitosas
            almacen_id = registro_usado.get('id', '') if registro_usado else ""
            return all(resultados), almacen_id
        
        # Para operaciones "sumar" y "establecer", crear un nuevo registro
        now = get_current_datetime_str()
        
        nueva_entrada = {
            "id": generate_almacen_id(),
            "compra_id": compra_id,
            "tipo_cafe_origen": fase_normalizada,
            "fecha": now,
            "cantidad": cantidad_cambio,
            "fase_actual": fase_normalizada,
            "cantidad_actual": cantidad_cambio,
            "notas": f"Operación: {operacion}. {notas}",
            "fecha_actualizacion": now
        }
        
        # Añadir a la hoja
        resultado = append_data("almacen", nueva_entrada)
        
        if resultado:
            logger.info(f"Nuevo registro de almacén creado correctamente: {nueva_entrada['id']}")
            return True
        else:
            logger.error(f"Error al crear nuevo registro de almacén")
            return False
    except Exception as e:
        logger.error(f"Error al actualizar almacén: {e}")
        # Para las operaciones que no son de TOSTADO y restar, devolver un tuple (False, "")
        if operacion == "restar":
            return False, ""
        return False

def leer_almacen_para_proceso():
    """
    Lee los registros de almacén para mostrarlos en el comando /proceso.
    
    Returns:
        Dict: Diccionario con fases y cantidades disponibles
    """
    try:
        logger.info("Leyendo registros de almacén para proceso")
        
        # Obtener todos los registros de almacén
        almacen_data = get_all_data('almacen')
        
        if not almacen_data:
            logger.error(f"No se pudieron obtener datos de almacén")
            return {}
        
        # Agrupar y sumar por fase_actual
        resultados = {}
        for registro in almacen_data:
            fase_actual = str(registro.get('fase_actual', '')).strip().upper()
            if fase_actual in FASES_CAFE:
                # Sumar las cantidades disponibles por fase
                try:
                    kg_disponibles = safe_float(registro.get('cantidad_actual', '0'))
                    if fase_actual not in resultados:
                        resultados[fase_actual] = {
                            'cantidad_total': 0,
                            'registros': []
                        }
                    
                    if kg_disponibles > 0:
                        resultados[fase_actual]['cantidad_total'] += kg_disponibles
                        resultados[fase_actual]['registros'].append(registro)
                except (ValueError, TypeError) as e:
                    logger.error(f"Error al procesar cantidad_actual en almacén: {e}")
        
        return resultados
    except Exception as e:
        logger.error(f"Error al leer almacén para proceso: {e}")
        return {}

def sincronizar_almacen_con_compras():
    """
    Sincroniza el almacén con las existencias actuales en las compras.
    Útil para inicializar o corregir discrepancias.
    
    Returns:
        bool: True si se sincronizó correctamente, False en caso contrario
    """
    try:
        logger.info("Iniciando sincronización de almacén con compras")
        
        # Obtener todas las compras
        compras = get_all_data('compras')
        
        # Agrupar compras por tipo_cafe/fase
        compras_por_fase = {}
        for compra in compras:
            tipo_cafe = compra.get('tipo_cafe', '').strip().upper()
            if tipo_cafe and tipo_cafe in FASES_CAFE:
                if tipo_cafe not in compras_por_fase:
                    compras_por_fase[tipo_cafe] = []
                compras_por_fase[tipo_cafe].append(compra)
        
        # Crear nuevos registros en almacén para cada compra
        resultados = []
        for fase, compras_list in compras_por_fase.items():
            for compra in compras_list:
                try:
                    # Calcular cantidad
                    cantidad = safe_float(compra.get('cantidad', 0))
                    
                    # Verificar si ya existe un registro en almacén para esta compra
                    compra_id = compra.get('id', '')
                    if compra_id:
                        almacen_existente = get_filtered_data('almacen', {'compra_id': compra_id})
                        if almacen_existente:
                            logger.info(f"Ya existe registro en almacén para compra {compra_id}")
                            continue
                    
                    # Crear registro en almacén
                    if cantidad > 0:
                        now = get_current_datetime_str()
                        resultado = append_data('almacen', {
                            'id': generate_almacen_id(),
                            'compra_id': compra_id,
                            'tipo_cafe_origen': fase,
                            'fecha': now,
                            'cantidad': cantidad,
                            'fase_actual': fase,
                            'cantidad_actual': cantidad,
                            'notas': f"Sincronización automática - Compra ID: {compra_id}",
                            'fecha_actualizacion': now
                        })
                        resultados.append(resultado)
                        if resultado:
                            logger.info(f"Creado registro en almacén para compra {compra_id}")
                        else:
                            logger.warning(f"Error al crear registro en almacén para compra {compra_id}")
                except Exception as e:
                    logger.error(f"Error al procesar compra {compra.get('id', '')}: {e}")
                    resultados.append(False)
        
        # Verificar resultados
        if all(resultados):
            logger.info("Sincronización de almacén completada correctamente")
            return True
        else:
            logger.warning(f"Sincronización parcial: {resultados.count(True)}/{len(resultados)} operaciones exitosas")
            return resultados.count(True) > 0
    except Exception as e:
        logger.error(f"Error al sincronizar almacén con compras: {e}")
        return False