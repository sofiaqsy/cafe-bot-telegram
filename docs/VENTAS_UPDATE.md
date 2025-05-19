# Mejora en el Sistema de Ventas y Almacén de Café

## Problemas Identificados
1. **Problema con registros redundantes**: 
   Al realizar una venta de café TOSTADO, el sistema creaba un nuevo registro negativo en el almacén. Esto generaba registros redundantes y dificultaba el seguimiento del inventario real disponible.

2. **Problema con campos no guardados en ventas**:
   Los campos `peso`, `precio_kg`, `notas` y `registrado_por` no se estaban guardando correctamente en la hoja de ventas debido a una discrepancia entre los nombres de campos usados en ventas.py y los definidos en sheets.py.

## Solución Implementada
Hemos realizado las siguientes mejoras:

1. **Cambios en la estructura de datos**:
   - Se añadió una nueva columna `fecha_actualizacion` a la tabla `almacen` para registrar cuándo se modificó por última vez un registro.
   
2. **Cambios de funcionalidad**:
   - Se implementó una nueva función `update_almacen_tostado` en `utils/sheets.py` que actualiza directamente los registros existentes de café TOSTADO en lugar de crear nuevos registros negativos.
   - Se modificó la función `update_almacen` para que utilice la nueva función específica cuando se trata de restar café TOSTADO.

3. **Corrección de campos en ventas**:
   - Se actualizó el archivo `handlers/ventas.py` para usar los mismos nombres de campos que están definidos en los headers de `utils/sheets.py`.
   - Se cambiaron las referencias a `cantidad` por `peso` y a `precio` por `precio_kg`, asegurando que se guarden correctamente.
   - Se aseguró que el campo `registrado_por` se inicialice correctamente.

## Ventajas
- **Mayor claridad**: El historial de almacén muestra ahora solo los registros reales sin entradas negativas.
- **Mejor trazabilidad**: Se mantiene un registro de cuándo se actualizó cada entrada en el almacén.
- **Operaciones más eficientes**: Se reduce la cantidad de registros necesarios en la base de datos.
- **Datos completos**: Todos los campos de ventas ahora se guardan correctamente en la hoja de cálculo.

## Cómo funciona
1. Cuando se realiza una venta de café TOSTADO, el sistema busca los registros existentes de TOSTADO con inventario disponible.
2. En lugar de crear un nuevo registro negativo, actualiza los registros existentes, restando la cantidad vendida.
3. Se actualiza la fecha de actualización y se añade una nota detallando la operación.
4. Se mantiene el orden FIFO (primero en entrar, primero en salir) para gestionar el inventario.
5. Los nombres de campos en el módulo de ventas ahora coinciden exactamente con los definidos en los headers, asegurando una grabación completa de todos los datos.

## Extensiones Futuras
Esta mejora podría extenderse a otras fases del café como MOLIDO y VERDE si es necesario, siguiendo el mismo patrón implementado para TOSTADO.