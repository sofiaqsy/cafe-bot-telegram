# Corrección del Formato de Datos en la Función Adelanto

## Descripción del Problema

Al registrar un adelanto, los datos no se están guardando correctamente en la hoja de cálculo. Específicamente:

1. Las fechas y horas se guardan con comillas: '2025-05-20' en lugar de 2025-05-20
2. El proveedor no se guarda en la columna correcta
3. Los valores numéricos como "monto" y "saldo_restante" no se reconocen como números, sino como texto, y a veces se guardan en columnas incorrectas

Esto crea inconsistencias en los datos y hace difícil su consulta y manipulación.

## Causa del Problema

Después de analizar el código, se ha identificado que:

1. La función `append_data()` en `utils/sheets/core.py` está convirtiendo todos los valores a cadenas de texto, incluidos los valores numéricos
2. Google Sheets está interpretando de manera incorrecta los valores al recibir todo como texto
3. La opción de inserción `valueInputOption` está configurada como 'RAW' o se está enviando como strings, lo que provoca que Google Sheets no interprete correctamente los tipos de datos

## Cambios Realizados

1. **Tratamiento especial para campos numéricos**:
   - Convertir explícitamente los campos `monto` y `saldo_restante` a números flotantes para asegurar que Google Sheets los interprete correctamente
   - Usar la opción `valueInputOption="USER_ENTERED"` para que Google Sheets pueda interpretar automáticamente los tipos de datos

2. **Mejora en el manejo de fechas**:
   - Verificar si la fecha ya tiene el formato correcto antes de volver a formatearla
   - Asegurarse de que las fechas se guarden correctamente como fechas y no como texto

3. **Cambio en el método de inserción de datos**:
   - Utilizar `values().update()` en lugar de `appendCells()` para un mejor control de los tipos de datos
   - Formato condicional de valores según el tipo de campo

## Cómo Probar

1. Ejecutar el comando `/adelanto`
2. Ingresar un proveedor de prueba (ej. "Test")
3. Ingresar un monto (ej. "500")
4. Ingresar una nota opcional (ej. "Prueba")
5. Confirmar el adelanto
6. Verificar en la hoja de cálculo que los datos se han guardado correctamente:
   - La fecha sin comillas
   - El proveedor en la columna correcta
   - Los valores numéricos reconocidos como números y en las columnas correctas

## Implementación

Este cambio modifica principalmente la función `append_data()` en `utils/sheets/core.py`. La nueva implementación prioriza preservar los tipos de datos correctos y asegurarse de que lleguen correctamente a Google Sheets.