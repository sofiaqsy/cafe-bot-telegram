def update_almacen(fase, cantidad_cambio, operacion="sumar", notas="", compra_id=""):
    """
    Actualiza la cantidad disponible en el almacén para una fase específica
    
    Args:
        fase: Fase del café (CEREZO, MOTE, PERGAMINO, VERDE)
        cantidad_cambio: Cantidad a sumar o restar
        operacion: "sumar" para añadir, "restar" para disminuir, "establecer" para fijar valor
        notas: Notas adicionales sobre la operación
        compra_id: ID de compra relacionada (si aplica)
    
    Returns:
        bool or tuple: 
            - Si es una venta: (bool, str) donde el bool indica si se actualizó correctamente, y el str es el ID del almacén usado.
            - En otros casos: bool que indica si se actualizó correctamente.
    """
    try:
        import datetime
        
        logger.info(f"Actualizando almacén - Fase: {fase}, Cambio: {cantidad_cambio} kg, Operación: {operacion}, Compra ID: {compra_id}")
        
        # Si es TOSTADO y la operación es "restar", usar la nueva función
        if fase.strip().upper() == "TOSTADO" and operacion == "restar":
            return update_almacen_tostado(fase, cantidad_cambio, notas)
        
        # Normalizar fase
        fase_normalizada = fase.strip().upper()
        
        # Para operación "restar", debemos buscar registros existentes y actualizar la cantidad
        if operacion == "restar":
            # Obtener todos los registros de la fase con cantidad disponible
            almacen_data = get_filtered_data('almacen', {'fase_actual': fase_normalizada})
            
            if not almacen_data:
                logger.warning(f"No se encontraron registros de {fase_normalizada} en el almacén")
                return False, ""
            
            # Filtrar los que tienen cantidad disponible
            registros_con_disponible = []
            for registro in almacen_data:
                try:
                    kg_disponibles = float(str(registro.get('cantidad_actual', '0')).replace(',', '.'))
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
                    kg_disponibles = float(str(registro.get('cantidad_actual', '0')).replace(',', '.'))
                    
                    # Determinar cuánto restar de este registro
                    cantidad_a_restar = min(kg_disponibles, cantidad_restante)
                    nueva_cantidad = kg_disponibles - cantidad_a_restar
                    
                    # Actualizar en la hoja
                    row_index = registro.get('_row_index')
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
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
        else:
            # Crear nuevo registro para operaciones de "sumar" o "establecer"
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            nueva_entrada = {
                "id": generate_almacen_id(),
                "compra_id": compra_id,
                "tipo_cafe_origen": fase_normalizada,
                "fecha": now,
                "cantidad": cantidad_cambio if operacion in ["sumar", "establecer"] else -cantidad_cambio,
                "fase_actual": fase_normalizada,
                "cantidad_actual": cantidad_cambio if operacion in ["sumar", "establecer"] else 0,
                "notas": f"Operación: {operacion}. {notas}",
                "fecha_actualizacion": now
            }
            
            # Añadir a la hoja
            resultado = append_data("almacen", nueva_entrada)
            
            if resultado:
                logger.info(f"Nuevo registro de almacén creado correctamente: {nueva_entrada['id']}")
                # Para las operaciones que no son "restar", devolver sólo True
                return True
            else:
                logger.error(f"Error al crear nuevo registro de almacén")
                # Para las operaciones que no son "restar", devolver sólo False
                return False
    except Exception as e:
        logger.error(f"Error al actualizar almacén: {e}")
        # Para las operaciones "restar" devolver un tuple (False, "")
        if operacion == "restar":
            return False, ""
        return False