# Mejoras en la funcionalidad de Compra con Adelanto

Este documento explica las mejoras implementadas en la funcionalidad de compra con adelanto para el bot de Telegram de gestión de café.

## Cambios realizados

1. **Listado mejorado de adelantos disponibles**:
   - Ahora muestra todos los adelantos con saldos positivos agrupados por proveedor
   - Cada proveedor muestra su saldo total acumulado
   - Interfaz más amigable con botones interactivos

2. **Selección detallada de adelantos**:
   - Cuando un proveedor tiene múltiples adelantos, permite elegir:
     - Usar el saldo total de todos los adelantos
     - Seleccionar un adelanto específico (mostrando fecha y monto)

3. **Flujo de compra simplificado**:
   - Después de seleccionar el proveedor/adelanto, continúa con el flujo estándar:
     - Solicitud de cantidad de café (en kg)
     - Solicitud de precio por kg
     - Solicitud de calidad (1-5 estrellas)
     - Confirmación de la operación

4. **Procesamiento inteligente de adelantos**:
   - Si se usa el saldo total, se consumirán los adelantos más antiguos primero
   - Si se selecciona un adelanto específico, solo se usará ese
   - Actualización automática de los saldos en Google Sheets

5. **Mejora en la experiencia del usuario**:
   - Botones para cancelar o volver en cualquier momento
   - Mensajes descriptivos en cada paso
   - Resumen detallado antes de confirmar la operación
   - Confirmación completa al finalizar la compra

## Beneficios de esta implementación

- **Mayor control**: Los usuarios pueden elegir qué adelantos específicos usar
- **Transparencia**: Muestra claramente cómo se distribuye el pago entre adelanto y efectivo
- **Priorización automática**: Consume primero los adelantos más antiguos
- **Flexibilidad**: Permite usar parcial o totalmente los adelantos disponibles

## Ejemplo de uso

1. El usuario ejecuta `/compra_adelanto`
2. El bot muestra la lista de proveedores con adelantos disponibles
3. El usuario selecciona un proveedor
4. Si el proveedor tiene múltiples adelantos, el bot muestra las opciones:
   - Usar el saldo total
   - Seleccionar un adelanto específico
5. El usuario continúa con el flujo normal de compra (cantidad, precio, calidad)
6. El bot calcula automáticamente la distribución de pagos
7. El usuario confirma la operación
8. El bot registra la compra y actualiza los saldos de adelantos