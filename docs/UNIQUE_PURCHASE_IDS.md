# Implementación de IDs Únicos para Compras

## Descripción del problema

El sistema originalmente utilizaba índices de fila (`_row_index`) para referenciar las compras desde el módulo de proceso. Este enfoque presentaba varios problemas:

1. **Fragilidad**: Si el orden de las filas en la hoja de cálculo cambiaba (por eliminaciones o reordenamientos), las referencias dejaban de ser válidas.
2. **Identificación no explícita**: Los índices de fila no proporcionaban información semántica sobre la compra referenciada.
3. **Dificultad para trazabilidad**: No era fácil identificar qué compras habían sido procesadas.
4. **Problemas al exportar/importar**: Al mover datos entre sistemas, se perdía el contexto de las relaciones.

## Solución implementada

Se implementó un sistema de IDs únicos para cada compra, con las siguientes características:

1. **Identificadores alfanuméricos cortos**: Cada compra recibe un identificador único hexadecimal de 8 caracteres.
2. **Generación automática**: Los IDs se generan automáticamente al registrar una compra.
3. **Persistencia en Google Sheets**: Se añadió el campo 'id' a la estructura de datos de compras.
4. **Retrocompatibilidad**: El sistema actualiza automáticamente registros antiguos asignándoles IDs.
5. **Visualización explícita**: Los IDs se muestran en la interfaz de usuario al seleccionar compras.

## Componentes técnicos de la solución

### 1. Generación de IDs únicos

Se implementó una función `generate_unique_id()` en `utils/sheets.py` que utiliza el módulo `uuid` de Python para generar identificadores universalmente únicos, de los cuales se toman los primeros 8 caracteres:

```python
def generate_unique_id():
    """Genera un ID único para registros"""
    return str(uuid.uuid4().hex)[:8]  # Usar solo los primeros 8 caracteres para un ID más corto
```

### 2. Actualización del esquema de datos

Se modificó la estructura de cabeceras para incluir el campo 'id' en la hoja de compras:

```python
HEADERS = {
    'compras': ['id', 'fecha', 'tipo_cafe', 'proveedor', 'cantidad', 'precio', 'total', 'fase_actual', 'kg_disponibles'],
    # ...otros headers...
}
```

### 3. Asignación automática de IDs

Se añadió lógica en la función `append_data()` para asegurar que cada compra tenga un ID:

```python
# Para compras, asegurar que tenga un ID único
if sheet_name == 'compras' and 'id' not in data:
    data['id'] = generate_unique_id()
    logger.info(f"Generado ID único para compra: {data['id']}")
```

### 4. Migración de datos existentes

Se implementó código en `initialize_sheets()` para asignar IDs a las compras existentes:

```python
if sheet_name == 'compras' and (len(values[0]) < len(header) or 'id' not in values[0]):
    # ...
    # Para cada fila existente, añadir ID único si no existe
    for i, row in enumerate(existing_rows):
        row_num = i + 2  # +2 porque empezamos en la fila 2
        
        # Si la fila no tiene un ID (primera columna vacía o no existente)
        if len(row) == 0 or not row[0]:
            # Generar ID único
            new_id = generate_unique_id()
            
            # Actualizar ID en la primera columna
            sheets.values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A{row_num}",
                valueInputOption="RAW",
                body={"values": [[new_id]]}
            ).execute()
    # ...
```

### 5. Integración en el módulo de proceso

Se actualizó el módulo de proceso para utilizar y mostrar IDs:

- Se modificó la visualización de compras disponibles para mostrar sus IDs
- Se implementó el uso de IDs en lugar de índices al registrar procesos
- Se mejoró la interfaz de usuario para mostrar claramente los IDs

### 6. Función de consulta por fase

Se implementó una función especializada para obtener compras por fase:

```python
def get_compras_por_fase(fase):
    """
    Obtiene todas las compras en una fase específica con kg disponibles
    
    Args:
        fase: Fase actual del café (CEREZO, MOTE, PERGAMINO, etc.)
        
    Returns:
        Lista de compras en la fase especificada que aún tienen kg disponibles
    """
    try:
        compras = get_filtered_data('compras', {'fase_actual': fase})
        
        # Filtrar solo las que tienen kg disponibles > 0
        compras_disponibles = []
        for compra in compras:
            try:
                kg_disponibles = float(compra.get('kg_disponibles', 0))
                if kg_disponibles > 0:
                    compras_disponibles.append(compra)
            except (ValueError, TypeError):
                continue
                
        return compras_disponibles
    except Exception as e:
        logger.error(f"Error al obtener compras en fase {fase}: {e}")
        return []
```

## Beneficios de la implementación

1. **Mayor robustez**: Las referencias a compras permanecen válidas incluso si cambia el orden de las filas en Google Sheets.
2. **Mejor trazabilidad**: Los IDs únicos facilitan el seguimiento de cada compra a través del proceso.
3. **Mejora en la interfaz de usuario**: La visualización de IDs en la interfaz hace explícitas las relaciones.
4. **Facilidad para reportes**: Se pueden generar reportes que relacionen compras y procesos usando los IDs.
5. **Preparación para expansión**: Este diseño facilita futuras expansiones como la integración con sistemas externos.

## Consideraciones a futuro

1. **Índice para búsquedas**: Si el número de compras crece significativamente, podría ser útil implementar algún tipo de índice para optimizar búsquedas por ID.
2. **Exportación/importación**: Considerar herramientas para exportar/importar datos manteniendo la integridad de los IDs.
3. **Extensión a otros módulos**: Aplicar el mismo concepto de IDs únicos a otros tipos de registros como gastos, ventas, etc.