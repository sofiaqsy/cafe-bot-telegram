# Solución al error en la transición de pergamino a tostado

## Problema identificado

Al utilizar la funcionalidad de `/proceso` para transicionar café de estado pergamino a tostado, se producía el siguiente error:

```
2025-05-18T05:35:16.186970+00:00 app[worker.1]: 2025-05-18 05:35:16,186 - handlers.proceso - ERROR - Error al guardar proceso: append_data() missing 1 required positional argument: 'headers'
```

## Causa del error

El error se debe a una incompatibilidad entre la implementación de Google Sheets y la función original de `append_data()`. Al migrar del sistema de almacenamiento en CSV a Google Sheets, se produjeron los siguientes cambios:

1. En `utils/sheets.py`, la función `append_data()` requiere solo dos parámetros: `sheet_name` y `data` 
2. En `utils/db.py`, la función wrapper `append_data()` estaba exigiendo tres parámetros: `filename`, `row`, y `headers`
3. La función de sheets.py usa las cabeceras predefinidas internamente en su variable `HEADERS`, pero el código antiguo seguía pasando el parámetro `headers`

## Solución implementada

Se realizó el siguiente cambio para resolver el problema:

1. Se modificó la función `append_data()` en `utils/db.py` para hacer que el parámetro `headers` sea opcional:
   ```python
   def append_data(filename: str, row: Dict[str, Any], headers: Optional[List[str]] = None) -> bool:
   ```

2. Se reorganizó el código para verificar la existencia de `headers` antes de usarlo:
   ```python
   if headers:
       # Lógica de validación usando headers
   ```

3. Se mantuvo la validación de campos y la asignación de valores por defecto para mantener compatibilidad con el código existente

## Ventajas de esta solución

1. **Compatibilidad con código existente**: No es necesario modificar los manejadores que ya pasan `headers`
2. **Compatibilidad con la nueva implementación**: Funciona correctamente con la función de Google Sheets que no requiere `headers`
3. **Mayor robustez**: Se agregaron verificaciones adicionales para evitar errores con campos faltantes
4. **Tipado mejorado**: Se agregaron anotaciones de tipo correctas usando `Optional` para indicar claramente que el parámetro es opcional

## Pruebas realizadas

Se verificó que la funcionalidad `/proceso` funciona correctamente con esta corrección para:

- Transición de pergamino a tostado
- Otros tipos de transiciones de estados
- Integración con Google Sheets

## Conclusiones

Este cambio soluciona el problema manteniendo la compatibilidad hacia atrás y sin requerir cambios adicionales en otros archivos del proyecto. La solución es mínima y enfocada en el punto exacto del problema.
