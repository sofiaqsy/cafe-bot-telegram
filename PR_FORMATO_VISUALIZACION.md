# Mejora del formato de visualización en comando /EVIDENCIA

## Problema
Al ejecutar el comando `/EVIDENCIA` y seleccionar "Compras", la visualización de los registros no prioriza la información más relevante (proveedor, monto, tipo de café) en el formato actual.

## Solución
Se modificó el archivo `handlers/evidencias.py` para mejorar el formato de visualización en la selección de compras, mostrando la información en este orden:

1. Proveedor
2. Monto total (S/)
3. Tipo de café

## Cambios realizados
- Reorganización del formato de visualización para mostrar en la primera línea: `[proveedor], S/ [monto], [tipo_cafe]`
- El cambio se aplicó específicamente en la función `seleccionar_tipo` cuando se procesan las opciones de compra

## Cómo probar
1. Ejecutar el comando `/EVIDENCIA`
2. Seleccionar "🛒 Compras"
3. Verificar que ahora cada registro muestra un formato con esta estructura: `[proveedor], S/ [monto], [tipo_cafe], [fecha], [id]`
4. Comparar con el formato anterior para confirmar la mejora

## Impacto
Este cambio facilita la identificación visual de las compras al mostrar primero los datos más relevantes, lo que mejora la experiencia del usuario sin afectar otras funcionalidades.
