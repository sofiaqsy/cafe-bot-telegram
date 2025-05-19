# Mejora en el Sistema de Ventas y Almacén de Café

## Problema
Anteriormente, al realizar una venta de café TOSTADO, el sistema creaba un nuevo registro negativo en el almacén. Esto generaba registros redundantes y dificultaba el seguimiento del inventario real disponible.

## Solución Implementada
Hemos realizado las siguientes mejoras:

1. Se añadió una nueva columna `fecha_actualizacion` a la tabla `almacen` para registrar cuándo se modificó por última vez un registro.

2. Se implementó una nueva función `update_almacen_tostado` en `utils/sheets.py` que actualiza directamente los registros existentes de café TOSTADO en lugar de crear nuevos registros negativos.

3. Se modificó la función `update_almacen` para que utilice la nueva función específica cuando se trata de restar café TOSTADO.

## Ventajas
- **Mayor claridad**: El historial de almacén muestra ahora solo los registros reales sin entradas negativas.
- **Mejor trazabilidad**: Se mantiene un registro de cuándo se actualizó cada entrada en el almacén.
- **Operaciones más eficientes**: Se reduce la cantidad de registros necesarios en la base de datos.

## Cómo funciona
1. Cuando se realiza una venta de café TOSTADO, el sistema busca los registros existentes de TOSTADO con inventario disponible.
2. En lugar de crear un nuevo registro negativo, actualiza los registros existentes, restando la cantidad vendida.
3. Se actualiza la fecha de actualización y se añade una nota detallando la operación.
4. Se mantiene el orden FIFO (primero en entrar, primero en salir) para gestionar el inventario.

## Extensiones Futuras
Esta mejora podría extenderse a otras fases del café como MOLIDO y VERDE si es necesario, siguiendo el mismo patrón implementado para TOSTADO.
