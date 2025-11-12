# FLUJO DE ESTADOS - PEDIDOS WHATSAPP
## Bot de Telegram RosalCafe

### 📊 DIAGRAMA DE FLUJO DE ESTADOS

```
Pendiente
    ├──> ✅ Pedido confirmado
    └──> ❌ Cancelado (final)
    
Pedido confirmado
    ├──> 📦 En preparación
    └──> ❌ Cancelado (final)
    
En preparación
    ├──> 📮 Listo para envío
    └──> ❌ Cancelado (final)
    
Listo para envío
    ├──> 🚚 Enviado
    └──> ❌ Cancelado (final)
    
Enviado
    ├──> ✓ Entregado (final)
    └──> ❌ Cancelado (final)
    
Entregado ✓ (ESTADO FINAL - no puede cambiar)
Cancelado ❌ (ESTADO FINAL - no puede cambiar)
```

### 🎯 LÓGICA DE TRANSICIONES

**Estados finales (sin transiciones):**
- `Entregado`: El pedido fue entregado exitosamente
- `Cancelado`: El pedido fue cancelado en cualquier etapa

**Transiciones permitidas:**

| Estado Actual | Puede pasar a |
|--------------|---------------|
| Pendiente | Pedido confirmado, Cancelado |
| Pedido confirmado | En preparación, Cancelado |
| En preparación | Listo para envío, Cancelado |
| Listo para envío | Enviado, Cancelado |
| Enviado | Entregado, Cancelado |
| Entregado | (ninguno - estado final) |
| Cancelado | (ninguno - estado final) |

### 💡 CARACTERÍSTICAS DEL SISTEMA

1. **Inteligencia de Flujo**: Solo muestra los estados a los que puede transicionar desde el estado actual
2. **Cancelación Flexible**: Se puede cancelar un pedido en cualquier momento (excepto si ya está entregado o cancelado)
3. **Estados Finales**: Una vez que un pedido llega a "Entregado" o "Cancelado", no se puede cambiar más
4. **Auditoría**: Cada cambio de estado se registra con timestamp y usuario en las observaciones

### 🔄 EJEMPLO DE USO

**Escenario 1: Flujo normal exitoso**
```
1. Cliente hace pedido → Pendiente ⏳
2. Admin confirma → Pedido confirmado ✅
3. Se prepara el pedido → En preparación 📦
4. Pedido empacado → Listo para envío 📮
5. Enviado por courier → Enviado 🚚
6. Cliente recibe → Entregado ✓ [FINAL]
```

**Escenario 2: Cancelación temprana**
```
1. Cliente hace pedido → Pendiente ⏳
2. Cliente cancela → Cancelado ❌ [FINAL]
```

**Escenario 3: Cancelación durante preparación**
```
1. Cliente hace pedido → Pendiente ⏳
2. Admin confirma → Pedido confirmado ✅
3. Se prepara el pedido → En preparación 📦
4. Problema con stock → Cancelado ❌ [FINAL]
```

### 📝 NOTAS TÉCNICAS

- Los estados se almacenan en la columna O (15) de Google Sheets
- Las observaciones con historial se guardan en la columna Q (17)
- El sistema tiene caché de 30 segundos para reducir llamadas a la API
- Cada cambio de estado activa una notificación al cliente por WhatsApp

### 🛠️ CONFIGURACIÓN EN EL CÓDIGO

```python
# Modificar transiciones si es necesario
TRANSICIONES_ESTADOS = {
    'Pendiente': ['confirmar', 'cancelado'],
    'Pedido confirmado': ['preparacion', 'cancelado'],
    'En preparación': ['listo', 'cancelado'],
    'Listo para envío': ['enviado', 'cancelado'],
    'Enviado': ['entregado', 'cancelado'],
    'Entregado': [],
    'Cancelado': []
}
```

### 🚀 DEPLOYMENT

1. Reemplazar el archivo `pedidos_whatsapp.py` en el directorio handlers
2. Reiniciar el bot de Telegram
3. Verificar que las transiciones funcionen correctamente
4. Probar con un pedido de prueba

### 📊 MÉTRICAS RECOMENDADAS

- Tiempo promedio en cada estado
- Porcentaje de cancelaciones por estado
- Tasa de conversión (Pendiente → Entregado)
- Estados donde más se cancela

---

**Fecha de creación**: 2025-11-12
**Autor**: Claude + Keyla
**Versión**: 2.0 - Con flujo inteligente de estados
