# Corrección para el comando /compra_mixta

## Problema

Actualmente, al ejecutar una compra mixta que utiliza un adelanto como parte del pago, se produce un error al intentar actualizar el saldo restante del adelanto. El problema específico es que la función `update_cell` espera que el parámetro `row_index` sea un entero, pero en `compra_mixta.py` se está pasando el valor de `adelanto_id` directamente, sin convertirlo.

En la función original, tenemos:

```python
result_adelanto = update_cell("adelantos", datos["adelanto_id"], "saldo_restante", nuevo_saldo_formateado)
```

Cuando debería ser:

```python
adelanto_id_int = int(datos["adelanto_id"])
result_adelanto = update_cell("adelantos", adelanto_id_int, "saldo_restante", nuevo_saldo_formateado)
```

## Solución

La solución consiste en:

1. Convertir explícitamente el `adelanto_id` a entero antes de pasarlo a la función `update_cell`
2. Corregir el formato de los mensajes de texto para evitar dobles barras invertidas (\\\\n)

## Implementación

Se ha creado un archivo `compra_mixta_corrected.py` con la versión corregida de la función `confirmar_step`. Luego, en `bot.py`, se importa esta función corregida y se reemplaza la del módulo original, permitiendo mantener el resto de la funcionalidad intacta.

```python
# En bot.py
from handlers.compra_mixta_corrected import confirmar_step
from handlers.compra_mixta import register_compra_mixta_handlers
# Reemplazar la función en el módulo original con la corregida
import handlers.compra_mixta
handlers.compra_mixta.confirmar_step = confirmar_step
```

## Consideraciones adicionales

- Se ha verificado que no haya otros problemas de sintaxis o lógica en la función corregida
- Se mantiene toda la funcionalidad original, solo se corrige el error específico
- Se han simplificado las secuencias de escape en los strings para mejorar la legibilidad
