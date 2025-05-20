# Simplificación del formato de visualización en comando /EVIDENCIA

## Problema
Al ejecutar el comando `/EVIDENCIA` y seleccionar "Compras", la visualización actual muestra demasiada información (fecha y ID junto con los datos principales), lo que dificulta la lectura rápida de la información más relevante.

## Solución
Se modificó el archivo `handlers/evidencias.py` para simplificar el formato de visualización, eliminando la fecha y reorganizando el ID al final, con lo que se logra:

1. Mostrar solo la información esencial: proveedor, monto y tipo de café
2. Mantener el ID accesible pero menos prominente
3. Eliminar la fecha que no es necesaria para la selección

## Cambios realizados
- Nueva estructura para compras: `[proveedor] | S/ [monto] | [tipo_cafe] | ID:[id]`
- Nueva estructura para ventas: `[cliente] | [producto] | ID:[id]`
- Actualización de la función `seleccionar_operacion` para extraer correctamente el ID con el nuevo formato
- Eliminación completa de la fecha en la visualización

## Comparación

### Antes:
```
[proveedor], S/ [monto], [tipo_cafe], [fecha], [id]
```

### Ahora:
```
[proveedor] | S/ [monto] | [tipo_cafe] | ID:[id]
```

## Cómo probar
1. Ejecutar el comando `/EVIDENCIA`
2. Seleccionar "🛒 Compras"
3. Verificar que ahora cada registro muestra solo la información esencial en un formato más limpio
4. Verificar que al seleccionar una compra, el sistema sigue identificando correctamente el ID

## Impacto
Esta simplificación mejora significativamente la experiencia de usuario al hacer más clara y directa la visualización, manteniendo toda la funcionalidad necesaria para identificar y seleccionar correctamente los registros.
