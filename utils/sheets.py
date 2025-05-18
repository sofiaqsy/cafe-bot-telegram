def get_almacen_cantidad(fase):
    """
    Obtiene la cantidad disponible de una fase específica del almacén
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, etc.)
    
    Returns:
        float: Cantidad disponible en kg
    """
    try:
        # Normalizar fase para búsqueda
        fase_buscada = fase.strip().upper()
        
        # Obtener datos de almacén filtrados por fase
        almacen_data = get_filtered_data('almacen', {'fase': fase_buscada})
        
        if not almacen_data:
            logger.warning(f"No se encontró la fase {fase_buscada} en el almacén")
            return 0.0
        
        # Tomar el primer registro que coincida
        registro = almacen_data[0]
        
        # Convertir cantidad a float
        try:
            cantidad = float(str(registro.get('cantidad', '0')).replace(',', '.'))
            logger.info(f"Cantidad en almacén para fase {fase_buscada}: {cantidad} kg")
            return cantidad
        except (ValueError, TypeError) as e:
            logger.error(f"Error al convertir cantidad en almacén: {e}")
            return 0.0
    except Exception as e:
        logger.error(f"Error al obtener cantidad en almacén para fase {fase}: {e}")
        return 0.0

def update_almacen(fase, cantidad_cambio, operacion="sumar", notas=""):
    """
    Actualiza la cantidad disponible en el almacén para una fase específica
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, etc.)
        cantidad_cambio: Cantidad a sumar o restar
        operacion: "sumar" para añadir, "restar" para disminuir, "establecer" para fijar valor
        notas: Notas adicionales sobre la operación
    
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    try:
        import datetime
        
        logger.info(f"Actualizando almacén - Fase: {fase}, Cambio: {cantidad_cambio} kg, Operación: {operacion}")
        
        # Normalizar fase
        fase_normalizada = fase.strip().upper()
        
        # Obtener datos actuales del almacén para esta fase
        almacen_data = get_filtered_data('almacen', {'fase': fase_normalizada})
        
        # Si no existe la fase, verificar si es válida y añadirla
        if not almacen_data:
            if fase_normalizada in FASES_CAFE:
                logger.info(f"Fase {fase_normalizada} no encontrada en almacén. Creando...")
                
                # Crear nuevo registro para esta fase
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cantidad_final = cantidad_cambio if operacion in ["sumar", "establecer"] else 0
                
                nueva_entrada = {
                    "fase": fase_normalizada,
                    "cantidad": cantidad_final,
                    "ultima_actualizacion": now,
                    "notas": f"Fase creada. {notas}"
                }
                
                # Añadir a la hoja
                return append_data("almacen", nueva_entrada)
            else:
                logger.error(f"Fase {fase_normalizada} no válida para almacén")
                return False
        
        # Obtener registro y su índice
        registro = almacen_data[0]
        row_index = registro.get('_row_index')
        
        # Convertir cantidad actual a float
        try:
            cantidad_actual = float(str(registro.get('cantidad', '0')).replace(',', '.'))
        except (ValueError, TypeError):
            logger.warning(f"Cantidad actual no válida: {registro.get('cantidad')}. Usando 0.")
            cantidad_actual = 0.0
        
        # Calcular nueva cantidad según la operación
        if operacion == "sumar":
            nueva_cantidad = cantidad_actual + float(cantidad_cambio)
        elif operacion == "restar":
            nueva_cantidad = max(0, cantidad_actual - float(cantidad_cambio))  # Nunca menor que 0
        elif operacion == "establecer":
            nueva_cantidad = max(0, float(cantidad_cambio))  # Nunca menor que 0
        else:
            logger.error(f"Operación no válida: {operacion}")
            return False
        
        # Redondear a 2 decimales
        nueva_cantidad = round(nueva_cantidad, 2)
        
        # Actualizar campos
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Actualizar cantidad
        update_cell("almacen", row_index, "cantidad", nueva_cantidad)
        
        # Actualizar fecha
        update_cell("almacen", row_index, "ultima_actualizacion", now)
        
        # Actualizar notas (añadir a las existentes)
        notas_actuales = registro.get('notas', '')
        nuevas_notas = f"{notas_actuales}; {now}: {operacion.capitalize()} {cantidad_cambio} kg - {notas}"[:250]  # Limitar longitud
        update_cell("almacen", row_index, "notas", nuevas_notas)
        
        logger.info(f"Almacén actualizado - Fase: {fase_normalizada}, Nueva cantidad: {nueva_cantidad} kg")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar almacén: {e}")
        return False

def actualizar_almacen_desde_proceso(origen, destino, cantidad, merma):
    """
    Actualiza el almacén basado en un proceso de transformación
    
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

def sincronizar_almacen_con_compras():
    """
    Sincroniza el almacén con las existencias actuales en las compras.
    Útil para inicializar o corregir discrepancias.
    
    Returns:
        bool: True si se sincronizó correctamente, False en caso contrario
    """
    try:
        logger.info("Iniciando sincronización de almacén con compras")
        
        # Para cada fase, calcular la suma total de kg disponibles
        totales_por_fase = {}
        for fase in FASES_CAFE:
            compras = get_compras_por_fase(fase)
            total_kg = sum(float(str(compra.get('kg_disponibles', '0')).replace(',', '.')) for compra in compras)
            totales_por_fase[fase] = round(total_kg, 2)
            logger.info(f"Fase {fase}: {total_kg} kg disponibles en compras")
        
        # Actualizar cada fase en el almacén
        import datetime
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for fase, total in totales_por_fase.items():
            update_almacen(
                fase=fase,
                cantidad_cambio=total,
                operacion="establecer",
                notas=f"Sincronización automática con compras ({now})"
            )
        
        logger.info("Sincronización de almacén completada")
        return True
    except Exception as e:
        logger.error(f"Error al sincronizar almacén: {e}")
        return False