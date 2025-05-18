# Corrección del Formato de Fechas en Google Sheets

## Problema

Google Sheets tiene una característica que convierte automáticamente los valores que parecen fechas a un formato numérico interno. Esto puede causar problemas de visualización como los siguientes:

- Las fechas se muestran como números (como `45795.04447` en lugar de `2025-05-08 13:14`)
- El formato de las fechas es inconsistente entre diferentes filas
- Al importar/exportar datos, los formatos pueden perderse

Este problema afectaba principalmente a la hoja de "compras", donde los datos de fechas se estaban mostrando incorrectamente.

## Solución implementada

Se implementó una solución integral que aborda el problema en tres niveles:

### 1. Prevención en Nuevos Registros

- Se agregó una función `format_date_for_sheets` en `utils/helpers.py` que añade una comilla simple (`'`) al inicio de las fechas, lo que hace que Google Sheets las trate como texto y mantenga su formato original.
- Esta función maneja diferentes formatos de entrada: cadenas, objetos `datetime`, objetos `date`, etc.
- Se actualizó el handler de compras para usar esta función antes de guardar los datos.

### 2. Actualización de Registros Existentes

- La función `initialize_sheets()` en `utils/sheets.py` ahora busca columnas de fecha en todas las hojas y verifica su formato.
- Cuando encuentra fechas con formato incorrecto, las actualiza automáticamente.
- Este proceso se ejecuta cada vez que se inicia el bot, asegurando que las fechas estén siempre correctamente formateadas.

### 3. Herramienta de Mantenimiento

- Se agregó un script `fix_date_formats.py` que puede ejecutarse para corregir todas las fechas en todas las hojas.
- Esta herramienta es útil como mantenimiento único para corregir registros históricos.
- El script incluye logs detallados para seguir el proceso de corrección.

## Detalles técnicos

### Función de Formateo

```python
def format_date_for_sheets(date_str):
    """
    Formatea una fecha para Google Sheets para evitar conversiones automáticas.
    Añade comilla simple al inicio para preservar el formato.
    """
    if not date_str:
        return ""
    
    if isinstance(date_str, str):
        # Si ya tiene comilla simple al inicio, simplemente devolver
        if date_str.startswith("'"):
            return date_str
        # Si es una fecha en formato estándar, añadir comilla simple
        if "-" in date_str:
            return f"'{date_str}"
    
    # Si es un objeto datetime, convertir a string
    if isinstance(date_str, datetime.datetime):
        return f"'{date_str.strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Si es una fecha, convertir a string
    if isinstance(date_str, datetime.date):
        return f"'{date_str.strftime('%Y-%m-%d')}"
    
    # En cualquier otro caso, devolver como string
    return str(date_str)
```

### Integración con Google Sheets

En la función `append_data()` de `utils/sheets.py`, se actualizó el código para formatear correctamente las fechas:

```python
# Pre-procesamiento específico para el campo de fecha
if 'fecha' in data and data['fecha']:
    # Asegurarse de que la fecha tiene un formato correcto
    # Si es un formato de fecha estándar (YYYY-MM-DD o YYYY-MM-DD HH:MM:SS)
    if isinstance(data['fecha'], str) and "-" in data['fecha']:
        # Añadir comilla simple para preservar formato de fecha
        if not data['fecha'].startswith("'"):
            data['fecha'] = "'" + data['fecha']
        logger.info(f"Fecha formateada como texto: {data['fecha']}")
```

### Script de Corrección

El script `fix_date_formats.py` busca todas las columnas que contienen "fecha" en su nombre y aplica la corrección a todas ellas:

```python
# Identificar columnas de fecha
date_columns = []
for column in HEADERS[sheet_name]:
    if 'fecha' in column.lower():
        date_columns.append(column)

# Procesar cada fila
for row in data:
    row_index = row.get('_row_index')
    if row_index is None:
        continue
    
    # Procesar cada columna de fecha
    for date_column in date_columns:
        date_value = row.get(date_column)
        if not date_value:
            continue
        
        # Si no tiene el formato correcto (prefijo de comilla simple)
        if not str(date_value).startswith("'"):
            # Formatear correctamente
            formatted_date = format_date_for_sheets(date_value)
            
            # Actualizar celda
            success = update_cell(sheet_name, row_index, date_column, formatted_date)
```

## Uso de la solución

### En desarrollo normal

No es necesario hacer nada especial. El código ya está configurado para manejar correctamente las fechas en todos los lugares donde se procesan datos.

### Para corregir datos existentes

Si hay datos con formatos incorrectos en la hoja de cálculo, se puede ejecutar el script de corrección:

```bash
python fix_date_formats.py
```

Este script:
1. Identifica todas las columnas con fechas
2. Revisa cada celda en esas columnas
3. Aplica el formato correcto a las que lo necesiten
4. Registra los cambios realizados

### Beneficios adicionales

Esta solución:
1. Garantiza consistencia en el formato de fechas en todas las hojas
2. Facilita el procesamiento posterior de los datos
3. Mejora la experiencia del usuario al visualizar la hoja de cálculo
4. Previene problemas similares en futuras actualizaciones

## Consideraciones a futuro

Si se implementan nuevas hojas con fechas, la función de formateo y el código existente seguirán funcionando correctamente sin necesidad de cambios adicionales. La única consideración es asegurarse de aplicar `format_date_for_sheets()` a cualquier nueva fecha que se vaya a guardar.