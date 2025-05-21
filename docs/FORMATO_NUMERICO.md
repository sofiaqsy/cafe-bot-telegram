# Guía de Implementación del Formato Numérico Estandarizado

Esta guía explica cómo implementar y utilizar el nuevo sistema de formato numérico estandarizado en el bot café-bot-telegram.

## Problema a resolver

- Inconsistencia en el formato de números en diferentes partes del sistema
- Confusión entre formato con punto decimal (1234.56) y formato con coma decimal (1.234,56)
- Incompatibilidad con visualización de Excel en configuración regional española/latinoamericana

## Solución implementada

Se ha creado un sistema centralizado de formateo numérico que:

1. Estandariza la presentación de números con coma como separador decimal y punto como separador de miles (1.234,56)
2. Permite al sistema aceptar entrada numérica en cualquier formato (con punto o coma como separador decimal)
3. Garantiza consistencia visual en todas las interfaces del bot

## Nuevas funciones disponibles

### En utils/formatters.py

- `formatear_numero(numero)`: Convierte cualquier número a formato estandarizado (ej: 1.234,56)
- `formatear_precio(precio)`: Formatea un precio con símbolo de moneda (ej: S/ 1.234,56)
- `procesar_entrada_numerica(entrada)`: Convierte texto ingresado por el usuario a valor numérico para operaciones internas

### Compatibilidad con código existente

Las funciones existentes en `utils/helpers.py` se han actualizado para usar internamente las nuevas funciones mientras mantienen la compatibilidad con el código existente:

- `format_currency()`: Ahora usa internamente `formatear_numero()`
- `safe_float()`: Ahora usa internamente `procesar_entrada_numerica()`

## Cómo implementar en nuevos módulos

1. Importar las funciones necesarias:
   ```python
   from utils.formatters import formatear_numero, formatear_precio, procesar_entrada_numerica
   ```

2. Para mostrar números al usuario (en mensajes de respuesta):
   ```python
   await update.message.reply_text(f"Monto: {formatear_precio(monto)}")
   ```

3. Para procesar entrada numérica del usuario:
   ```python
   try:
       monto = procesar_entrada_numerica(update.message.text)
       # Operaciones con el número...
   except ValueError as e:
       await update.message.reply_text(f"⚠️ {str(e)}")
   ```

## Ejemplo de implementación

```python
async def monto_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recibir monto ingresado por el usuario"""
    try:
        # Procesar entrada (acepta tanto "1,234.56" como "1.234,56")
        monto = procesar_entrada_numerica(update.message.text)
        
        if monto <= 0:
            await update.message.reply_text("⚠️ El monto debe ser mayor a cero")
            return MONTO
        
        # Confirmar al usuario con formato estandarizado
        await update.message.reply_text(
            f"Has ingresado: {formatear_precio(monto)}\n"
            "¿Es correcto? (Sí/No)"
        )
        
        context.user_data['monto'] = monto
        return CONFIRMAR
        
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {str(e)}")
        return MONTO
```

## Nuevos patrones a seguir

1. **En mensajes al usuario**: Usar siempre `formatear_precio()` o `formatear_numero()`
2. **Para procesar entrada de usuario**: Usar siempre `procesar_entrada_numerica()`
3. **Para cálculos internos**: Usar números con punto decimal (estándar de Python)
4. **Para mostrar resultados**: Convertir de nuevo a formato estandarizado

## Consideraciones para migración

- Todas las funciones antiguas siguen funcionando para mantener compatibilidad
- Se recomienda actualizar gradualmente todos los comandos al nuevo sistema

## Comandos actualizados

- `/adelanto`: Actualizado para usar el nuevo sistema de formateo
- Se recomienda actualizar progresivamente los demás comandos