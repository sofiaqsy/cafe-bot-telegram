# Implementación de Reportes Detallados para Análisis Financiero y de Inventario

## Descripción
Este PR implementa una nueva funcionalidad para generar reportes detallados a demanda que permiten analizar con mayor precisión los movimientos financieros y de inventario del negocio de café. La función permite obtener información detallada sobre:

- Kg de café comprados por día
- Gastos totales por día
- Métodos de pago (efectivo vs transferencia)
- Ingresos diarios
- Cálculo de ganancias (ingresos - gastos)

## Características Implementadas

1. **Nuevo comando `/reportes_detallados`** que ofrece tres opciones:
   - Reporte diario detallado (fecha actual)
   - Reporte por rango de fechas personalizado
   - Exportación a Excel con múltiples hojas de análisis

2. **Análisis detallado de métodos de pago** para entender el flujo de efectivo vs transferencias

3. **Cálculo de ganancias** basado en la diferencia entre ingresos por ventas y gastos totales

4. **Exportación a Excel** con hojas específicas para:
   - Reporte diario consolidado 
   - Análisis de tipos de café
   - Análisis de métodos de pago
   - Datos originales de compras, ventas, gastos y procesos

## Beneficios

- **Toma de decisiones informada**: Los reportes proporcionan datos claros para analizar la rentabilidad del negocio
- **Control de inventario mejorado**: Seguimiento preciso de los kg de café comprados, procesados y vendidos
- **Análisis de tendencias**: Al permitir reportes por rango de fechas, se pueden identificar patrones y tendencias
- **Exportación flexible**: La funcionalidad de Excel permite un análisis más profundo con herramientas externas

## Instrucciones de Uso

1. Usar el comando `/reportes_detallados` en el chat del bot
2. Seleccionar el tipo de reporte deseado:
   - "Reporte Diario Detallado" - muestra estadísticas del día actual
   - "Reporte por Rango de Fechas" - solicita fecha de inicio y fin
   - "Exportar a Excel" - genera un archivo Excel con análisis completo

## Notas Técnicas

- Se ha añadido un nuevo archivo `handlers/reportes_detallados.py` que contiene toda la lógica de reportes
- Se actualizó `bot.py` para registrar los nuevos handlers
- La implementación utiliza los datos existentes de las hojas de cálculo sin necesidad de modificar la estructura de datos
- Los métodos de pago se infieren a partir del campo "descripcion" en la hoja de gastos, buscando las palabras "efectivo" o "transferencia"

## Próximos Pasos

- Añadir gráficas a los reportes Excel para visualizar tendencias
- Implementar análisis de rentabilidad por tipo de café
- Añadir proyecciones de inventario basadas en tendencias históricas