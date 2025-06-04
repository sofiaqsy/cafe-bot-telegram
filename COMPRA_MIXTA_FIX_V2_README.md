# Corrección integral para el comando /compra_mixta

## Problema detectado

El comando `/compra_mixta` no funciona correctamente cuando se utiliza un adelanto como parte del pago. Se han identificado múltiples problemas:

1. **Error principal**: Cuando se intenta actualizar el saldo del adelanto, hay un error de tipo en la llamada a `update_cell`. El parámetro `row_index` espera un entero, pero `adelanto_id` se pasa como string, causando un error al intentar realizar la operación `row_index + 2` dentro de la función.

2. **Depuración insuficiente**: El código original no incluye suficientes logs de depuración para identificar la naturaleza exacta del problema en tiempo de ejecución.

3. **Secuencias de escape incorrectas**: Algunas cadenas de texto tienen secuencias de escape dobles (`\\n`), lo que causa problemas de formato en los mensajes enviados.

4. **Gestión de errores mejorable**: No se manejan correctamente algunos casos de error al procesar los adelantos.

## Solución implementada

Se ha creado una versión completamente revisada y corregida del módulo (`compra_mixta_v2.py`) que incluye:

1. **Conversión explícita de tipos**: Se asegura que `adelanto_id` se convierta correctamente a entero antes de pasarlo a `update_cell`:
   ```python
   adelanto_id_str = str(datos["adelanto_id"]).strip()
   debug_log(f"Adelanto ID como string: '{adelanto_id_str}'")
   adelanto_id_int = int(adelanto_id_str)
   debug_log(f"Adelanto ID convertido a entero: {adelanto_id_int}")
   
   # Luego se usa la variable convertida
   result_adelanto = update_cell("adelantos", adelanto_id_int, "saldo_restante", nuevo_saldo_formateado)
   ```

2. **Logs de depuración extensivos**: Se han añadido logs detallados en puntos críticos para facilitar la identificación de problemas:
   ```python
   debug_log(f"Adelanto ID original: {datos['adelanto_id']} - Tipo: {type(datos['adelanto_id'])}")
   debug_log(f"Calculando nuevo saldo: {datos.get('adelanto_saldo', 0)} - {datos.get('monto_adelanto', 0)} = {nuevo_saldo}")
   ```

3. **Corrección de formato de mensajes**: Se han eliminado las secuencias de escape dobles, reemplazando `\\n` por `\n`.

4. **Gestión de errores mejorada**: Se han añadido bloques try-except más específicos para manejar diferentes tipos de errores.

5. **Importación directa**: Se importa `update_cell` directamente para evitar problemas de referencia:
   ```python
   from utils.sheets import update_cell  # Importación directa
   ```

## Implementación

Para implementar esta corrección, se ha:

1. Creado un nuevo archivo `compra_mixta_v2.py` con la implementación corregida completa
2. Modificado `bot.py` para importar esta nueva versión del módulo
3. Mantenido la compatibilidad con la versión original como respaldo

El enfoque adoptado permite una transición limpia sin afectar otras partes del sistema, y facilita la reversión si fuera necesario.

## Pruebas realizadas

La nueva implementación ha sido probada verificando:
- Funcionamiento con diferentes métodos de pago
- Manejo correcto de los adelantos
- Actualización correcta del saldo restante en la hoja de adelantos
- Conversión adecuada de tipos de datos

## Consideraciones futuras

Para futuras mejoras, se sugiere:
1. Añadir más validaciones para prevenir errores similares
2. Implementar un sistema de pruebas automatizadas
3. Refactorizar la gestión de estados para hacerla más robusta
