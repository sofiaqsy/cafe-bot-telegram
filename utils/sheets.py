def append_data(sheet_name, data):
    """Añade una fila de datos a la hoja especificada"""
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        # Para compras, asegurar que tenga un ID único
        if sheet_name == 'compras' and 'id' not in data:
            data['id'] = generate_unique_id()
            logger.info(f"Generado ID único para compra: {data['id']}")
        
        # Convertir el diccionario a una lista ordenada según las cabeceras
        headers = HEADERS[sheet_name]
        row_data = []
        
        # Imprimir información detallada para depurar
        logger.info(f"Cabeceras para la hoja '{sheet_name}': {headers}")
        logger.info(f"Datos recibidos: {data}")
        
        # Verificar que todos los campos necesarios existan
        for header in headers:
            if header not in data or not data[header]:
                logger.warning(f"Campo '{header}' faltante o vacío en los datos. Usando valor por defecto.")
                
                # Valores por defecto según el campo
                if header == 'tipo_cafe':
                    data[header] = "No especificado"
                elif header in ['cantidad', 'precio', 'total', 'kg_disponibles', 'merma']:
                    data[header] = "0"
                elif header == 'fase_actual' and sheet_name == 'compras' and 'tipo_cafe' in data:
                    # Si es una compra, la fase inicial es el tipo de café
                    data[header] = data.get('tipo_cafe', "No especificado")
                else:
                    data[header] = ""
        
        # Pre-procesamiento específico para el campo de fecha
        # Para adelantos, asegurarnos de que las fechas tengan el formato correcto
        if sheet_name == 'adelantos':
            # Formatear explícitamente la fecha como texto para evitar que Sheets la convierta en número
            if 'fecha' in data and data['fecha']:
                # Asegurarse de que la fecha tiene el formato correcto (YYYY-MM-DD)
                # Si no sigue el formato, se deja como está
                if isinstance(data['fecha'], str) and len(data['fecha']) == 10 and data['fecha'][4] == '-' and data['fecha'][7] == '-':
                    # Prefijo con comilla simple para forzar formato de texto en Google Sheets
                    data['fecha'] = f"'{data['fecha']}'"
                    logger.info(f"Fecha formateada como texto: {data['fecha']}")
            
            # Hacer lo mismo con la hora
            if 'hora' in data and data['hora']:
                # Asegurarse de que la hora tiene el formato correcto (HH:MM:SS)
                # Si no sigue el formato, se deja como está
                if isinstance(data['hora'], str) and len(data['hora']) == 8 and data['hora'][2] == ':' and data['hora'][5] == ':':
                    # Prefijo con comilla simple para forzar formato de texto
                    data['hora'] = f"'{data['hora']}'"
                    logger.info(f"Hora formateada como texto: {data['hora']}")
        
        # Construir la fila de datos ordenada según las cabeceras
        for header in headers:
            row_data.append(data.get(header, ""))
        
        logger.info(f"Añadiendo datos a '{sheet_name}': {data}")
        logger.info(f"Datos formateados para Sheets: {row_data}")
        
        range_name = f"{sheet_name}!A:Z"
        result = sheets.values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_data]}
        ).execute()
        
        logger.info(f"Datos añadidos correctamente a '{sheet_name}'. Respuesta: {result}")
        return True
    except Exception as e:
        logger.error(f"Error al añadir datos a {sheet_name}: {e}")
        return False

def update_cell(sheet_name, row_index, column_name, value):
    """Actualiza una celda específica en la hoja de cálculo.
    
    Args:
        sheet_name: Nombre de la hoja
        row_index: Índice de la fila (basado en 0 para las filas de datos, excluyendo las cabeceras)
        column_name: Nombre de la columna
        value: Nuevo valor para la celda
    
    Returns:
        bool: True si se actualizó correctamente, False en caso contrario
    """
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        # Obtener índice de la columna
        headers = HEADERS[sheet_name]
        if column_name not in headers:
            logger.error(f"Nombre de columna inválido: {column_name}")
            raise ValueError(f"Nombre de columna inválido: {column_name}")
        
        column_index = headers.index(column_name)
        
        # Convertir índice de fila (desde 0) a número de fila real en la hoja (desde 1, contando cabeceras)
        # Fila 1 son las cabeceras, los datos comienzan en la fila 2
        real_row = row_index + 2
        
        # Convertir índice de columna a letra de columna de Excel (A, B, C, ...)
        column_letter = chr(65 + column_index)  # 65 es el código ASCII para 'A'
        cell_reference = f"{column_letter}{real_row}"
        
        # Pre-procesamiento para campos específicos
        if sheet_name == 'adelantos' and column_name == 'fecha':
            # Asegurarse de que la fecha tiene el formato correcto (YYYY-MM-DD)
            if isinstance(value, str) and len(value) == 10 and value[4] == '-' and value[7] == '-':
                # Prefijo con comilla simple para forzar formato de texto en Google Sheets
                value = f"'{value}'"
                logger.info(f"Fecha formateada como texto para actualización: {value}")
        
        logger.info(f"Actualizando celda {cell_reference} en hoja '{sheet_name}' con valor: {value}")
        
        # Actualizar celda
        result = sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!{cell_reference}",
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]}
        ).execute()
        
        logger.info(f"Celda actualizada correctamente. Respuesta: {result}")
        return True
    except Exception as e:
        logger.error(f"Error al actualizar celda: {e}")
        return False

def get_all_data(sheet_name):
    """Obtiene todos los datos de la hoja especificada"""
    if sheet_name not in HEADERS:
        logger.error(f"Nombre de hoja inválido: {sheet_name}")
        raise ValueError(f"Nombre de hoja inválido: {sheet_name}")
    
    try:
        spreadsheet_id = get_or_create_sheet()
        sheets = get_sheet_service()
        
        range_name = f"{sheet_name}!A:Z"
        result = sheets.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.info(f"No hay datos en la hoja '{sheet_name}'")
            return []
        
        # Convertir filas a diccionarios usando las cabeceras
        headers = values[0]
        rows = []
        
        for i, row in enumerate(values[1:]):  # Saltar la fila de cabeceras
            # Asegurarse de que la fila tenga la misma longitud que las cabeceras
            row_padded = row + [""] * (len(headers) - len(row))
            # Añadir el _row_index para referencia futura (basado en 0)
            row_dict = dict(zip(headers, row_padded))
            row_dict['_row_index'] = i
            rows.append(row_dict)
        
        logger.info(f"Obtenidos {len(rows)} registros de '{sheet_name}'")
        return rows
    except Exception as e:
        logger.error(f"Error al obtener datos de {sheet_name}: {e}")
        return []

def get_filtered_data(sheet_name, filters=None, days=None):
    """
    Obtiene datos filtrados de la hoja especificada
    
    Args:
        sheet_name: Nombre de la hoja
        filters: Diccionario de filtros campo:valor
        days: Si se proporciona, filtra por entradas en los últimos X días
    """
    all_data = get_all_data(sheet_name)
    
    if not all_data:
        return []
    
    filtered_data = all_data
    
    # Aplicar filtros
    if filters:
        # Para cada clave:valor de filtro, verificar coincidencia
        filtered_data = []
        for row in all_data:
            match = True
            for key, value in filters.items():
                # Normalizar valores para comparación (convertir a mayúsculas y eliminar espacios adicionales)
                row_value = str(row.get(key, '')).strip().upper()
                filter_value = str(value).strip().upper()
                
                if row_value != filter_value:
                    match = False
                    break
            
            if match:
                filtered_data.append(row)
    
    # Aplicar filtro de fecha (para futura implementación)
    if days:
        # TODO: Implementar filtrado por fecha
        pass
    
    logger.info(f"Filtrado: de {len(all_data)} registros a {len(filtered_data)} registros")
    return filtered_data

def es_transicion_valida(origen, destino):
    """Verifica si la transición de fase es válida
    
    Args:
        origen: Fase de origen
        destino: Fase de destino
        
    Returns:
        bool: True si la transición es válida, False en caso contrario
    """
    if origen not in TRANSICIONES_PERMITIDAS:
        return False
    
    return destino in TRANSICIONES_PERMITIDAS[origen]

def get_compras_por_fase(fase):
    """
    Obtiene todas las compras en una fase específica con kg disponibles
    
    Args:
        fase: Fase actual del café (CEREZO, MOTE, PERGAMINO, etc.)
        
    Returns:
        Lista de compras en la fase especificada que aún tienen kg disponibles
    """
    try:
        logger.info(f"Buscando compras en fase: {fase}")
        # Obtener todas las compras
        all_compras = get_all_data('compras')
        
        # Filtrar manualmente para evitar problemas de formato
        compras_disponibles = []
        for compra in all_compras:
            # Normalizar fase para comparación
            fase_actual = str(compra.get('fase_actual', '')).strip().upper()
            fase_buscada = str(fase).strip().upper()
            
            # Verificar si hay coincidencia de fase
            if fase_actual == fase_buscada:
                try:
                    # Verificar kg disponibles
                    kg_disponibles = float(str(compra.get('kg_disponibles', '0')).replace(',', '.'))
                    if kg_disponibles > 0:
                        # Agregar a la lista de compras disponibles
                        logger.info(f"Compra encontrada: {compra.get('proveedor')} - {kg_disponibles} kg - ID: {compra.get('id')}")
                        compras_disponibles.append(compra)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error al convertir kg_disponibles: {e}. Valor: {compra.get('kg_disponibles')}")
                    continue
        
        logger.info(f"Total compras encontradas en fase {fase}: {len(compras_disponibles)}")
        return compras_disponibles
    except Exception as e:
        logger.error(f"Error al obtener compras en fase {fase}: {e}")
        return []