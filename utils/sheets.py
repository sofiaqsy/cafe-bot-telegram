def initialize_sheets():
    """Inicializa las hojas de cálculo con las cabeceras si están vacías"""
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        # Verificar y configurar cada hoja
        for sheet_name, header in HEADERS.items():
            try:
                # Obtener datos actuales
                range_name = f"{sheet_name}!A1:Z1"
                result = sheets.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                
                # Si la hoja está vacía o no tiene cabeceras, agregarlas
                if not values:
                    logger.info(f"Inicializando hoja '{sheet_name}' con cabeceras: {header}")
                    sheets.values().update(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption="RAW",
                        body={"values": [header]}
                    ).execute()
                    logger.info(f"Hoja '{sheet_name}' inicializada con cabeceras")
                    
                    # Inicializar almacén con todas las fases si es la hoja de almacén
                    if sheet_name == 'almacen':
                        initialize_almacen()
                else:
                    # Verificar si las cabeceras existentes coinciden con las esperadas
                    logger.info(f"Cabeceras existentes en hoja '{sheet_name}': {values[0]}")
                    logger.info(f"Cabeceras esperadas: {header}")
                    
                    # Para compras, añadir campo id si no existe
                    if sheet_name == 'compras' and (len(values[0]) < len(header) or 'id' not in values[0]):
                        # Si hay que actualizar las cabeceras
                        logger.warning(f"Actualizando cabeceras de '{sheet_name}' para incluir ID y otros campos nuevos")
                        
                        # Actualizar cabeceras
                        sheets.values().update(
                            spreadsheetId=spreadsheet_id,
                            range=range_name,
                            valueInputOption="RAW",
                            body={"values": [header]}
                        ).execute()
                        
                        # Inicializar nuevas columnas para filas existentes
                        data_range_name = f"{sheet_name}!A2:Z"
                        existing_data = sheets.values().get(
                            spreadsheetId=spreadsheet_id,
                            range=data_range_name
                        ).execute()
                        
                        existing_rows = existing_data.get('values', [])
                        if existing_rows:
                            # Para cada fila existente, añadir ID único si no existe
                            for i, row in enumerate(existing_rows):
                                row_num = i + 2  # +2 porque empezamos en la fila 2 (después de las cabeceras)
                                
                                # Si la fila no tiene un ID (primera columna vacía o no existente)
                                if len(row) == 0 or not row[0]:
                                    # Generar ID único
                                    new_id = generate_unique_id()
                                    
                                    # Actualizar ID en la primera columna
                                    sheets.values().update(
                                        spreadsheetId=spreadsheet_id,
                                        range=f"{sheet_name}!A{row_num}",  # A es id (columna 1)
                                        valueInputOption="RAW",
                                        body={"values": [[new_id]]}
                                    ).execute()
                                    logger.info(f"Agregado ID único {new_id} a la fila {row_num}")
                                
                                # Si tiene tipo_cafe pero no fase_actual
                                if len(row) > 2 and row[2] and (len(row) <= 7 or not row[7]):  # 2 es el índice de tipo_cafe, 7 de fase_actual
                                    tipo_cafe = row[2]
                                    
                                    # Actualizar fase_actual = tipo_cafe
                                    sheets.values().update(
                                        spreadsheetId=spreadsheet_id,
                                        range=f"{sheet_name}!H{row_num}",  # H es fase_actual (columna 8)
                                        valueInputOption="RAW",
                                        body={"values": [[tipo_cafe]]}
                                    ).execute()
                                    logger.info(f"Actualizada fase_actual en fila {row_num}")
                                
                                # Si tiene cantidad pero no kg_disponibles
                                if len(row) > 4 and row[4] and (len(row) <= 8 or not row[8]):  # 4 es el índice de cantidad, 8 de kg_disponibles
                                    try:
                                        kg_disponibles = row[4]  # Usar el mismo valor que cantidad
                                        sheets.values().update(
                                            spreadsheetId=spreadsheet_id,
                                            range=f"{sheet_name}!I{row_num}",  # I es kg_disponibles (columna 9)
                                            valueInputOption="RAW",
                                            body={"values": [[kg_disponibles]]}
                                        ).execute()
                                        logger.info(f"Actualizada kg_disponibles en fila {row_num}")
                                    except Exception as e:
                                        logger.error(f"Error al actualizar kg_disponibles en fila {row_num}: {e}")
                        
                        logger.info(f"Actualización de datos existentes completada para '{sheet_name}'")
                    else:
                        logger.info(f"No hay datos existentes que actualizar en '{sheet_name}'")
                    
                    # Si hay otras diferencias, actualizar las cabeceras
                    if values and values[0] != header:
                        logger.warning(f"Las cabeceras existentes no coinciden con las esperadas. Actualizando...")
                        sheets.values().update(
                            spreadsheetId=spreadsheet_id,
                            range=range_name,
                            valueInputOption="RAW",
                            body={"values": [header]}
                        ).execute()
                        logger.info(f"Cabeceras actualizadas en hoja '{sheet_name}'")
                    
                    # Verificar si el almacén tiene todas las fases
                    if sheet_name == 'almacen':
                        verify_almacen_fases()
            except Exception as e:
                logger.error(f"Error al inicializar la hoja '{sheet_name}': {e}")
                raise
                
    except Exception as e:
        logger.error(f"Error al inicializar las hojas: {e}")
        raise

def initialize_almacen():
    """Inicializa la hoja de almacén con todas las fases posibles con 0 kg"""
    try:
        logger.info("Inicializando hoja de almacén con todas las fases")
        import datetime
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_to_append = []
        
        for fase in FASES_CAFE:
            # Crear una fila para cada fase posible con cantidad 0
            row = {
                "fase": fase,
                "cantidad": 0,
                "ultima_actualizacion": now,
                "notas": "Inicialización automática"
            }
            data_to_append.append(row)
            
        # Añadir todas las filas a la hoja
        for row in data_to_append:
            append_data("almacen", row)
            
        logger.info(f"Almacén inicializado con {len(FASES_CAFE)} fases")
        return True
    except Exception as e:
        logger.error(f"Error al inicializar almacén: {e}")
        return False

def verify_almacen_fases():
    """Verifica que el almacén tenga todas las fases posibles y añade las que falten"""
    try:
        almacen_data = get_all_data("almacen")
        fases_existentes = [row.get('fase', '').strip().upper() for row in almacen_data]
        fases_faltantes = [fase for fase in FASES_CAFE if fase not in fases_existentes]
        
        if fases_faltantes:
            logger.info(f"Faltan {len(fases_faltantes)} fases en el almacén: {fases_faltantes}")
            import datetime
            
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            for fase in fases_faltantes:
                row = {
                    "fase": fase,
                    "cantidad": 0,
                    "ultima_actualizacion": now,
                    "notas": "Fase añadida automáticamente"
                }
                append_data("almacen", row)
                
            logger.info(f"Añadidas {len(fases_faltantes)} fases al almacén")
        else:
            logger.info("El almacén ya tiene todas las fases necesarias")
            
        return True
    except Exception as e:
        logger.error(f"Error al verificar fases del almacén: {e}")
        return False