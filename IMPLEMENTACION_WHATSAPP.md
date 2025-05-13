# Implementación de WhatsApp para Café Bot

Este documento explica cómo integrar WhatsApp con el bot de Telegram para gestión de café, enfocándose principalmente en la recepción de pedidos de clientes.

## Comparación: WhatsApp vs Telegram

### Telegram (Implementación actual)
**Ventajas:**
- API gratuita y bien documentada
- Fácil de implementar
- Excelente para operaciones internas
- Soporte nativo para bots
- Sin restricciones de uso

**Desventajas:**
- Menor adopción por parte de clientes finales
- Requiere que los clientes tengan Telegram

### WhatsApp
**Ventajas:**
- Mayor base de usuarios
- Más familiar para clientes
- Mejor para atención al cliente
- Notificaciones más confiables

**Desventajas:**
- API más restrictiva
- Implementación más compleja
- Posibles costos (API oficial)
- Limitaciones en el formato de mensajes

## Opciones de Implementación para WhatsApp

### 1. WhatsApp Business API (Oficial)
- ✅ Oficial y confiable
- ✅ Soporte de Meta
- ❌ Requiere aprobación de empresa
- ❌ Costos por mensaje
- ❌ Proceso de setup complejo

### 2. Bibliotecas no oficiales (whatsapp-web.js)
- ✅ Gratuito
- ✅ Fácil de implementar
- ✅ Simula WhatsApp Web
- ❌ No oficial (puede dejar de funcionar)
- ❌ Requiere mantener sesión activa

### 3. Servicios de terceros (Twilio, MessageBird)
- ✅ Fácil integración
- ✅ Soporte profesional
- ✅ Escalable
- ❌ Costos mensuales/por mensaje
- ❌ Dependencia de terceros

## Recomendación para tu caso

Para un negocio de café, se recomienda un **enfoque híbrido**:

### 1. Mantén Telegram para operaciones internas
- Compras
- Procesamiento
- Gastos
- Ventas
- Reportes
- Adelantos

### 2. Agrega WhatsApp solo para pedidos de clientes
- Recepción de pedidos
- Confirmación de entregas
- Atención al cliente

### 3. Integración entre ambos sistemas
```
Cliente (WhatsApp) → Pedido → Base de datos → Notificación (Telegram)
```

## Implementación paso a paso

### Requisitos
1. Node.js 14 o superior
2. npm (gestor de paquetes de Node.js)
3. Cuenta de WhatsApp con número de teléfono

### Instalación

1. Crea un directorio para el bot de WhatsApp:
```bash
mkdir -p whatsapp_bot
cd whatsapp_bot
```

2. Inicializa el proyecto:
```bash
npm init -y
```

3. Instala las dependencias:
```bash
npm install whatsapp-web.js qrcode-terminal
```

4. Crea el archivo principal (whatsapp_bot.js):
```javascript
const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');

// Configuración del cliente
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: {
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Genera el código QR para iniciar sesión
client.on('qr', qr => {
    qrcode.generate(qr, { small: true });
    console.log('Escanea este código QR con WhatsApp');
});

client.on('ready', () => {
    console.log('Cliente WhatsApp está listo!');
});

// Maneja los mensajes entrantes
client.on('message', async msg => {
    // Implementar lógica de pedidos aquí
});

// Inicializa el cliente
client.initialize();
```

5. Ejecuta el bot:
```bash
node whatsapp_bot.js
```

6. Escanea el código QR con tu teléfono para autenticar WhatsApp.

## Integración con el sistema existente

Para integrar WhatsApp con el sistema actual de Telegram:

1. **Usa la misma base de datos**: Configura el bot de WhatsApp para leer/escribir en los mismos archivos CSV o Google Sheets que usa el bot de Telegram.

2. **Implementa notificaciones cruzadas**: Cuando se reciba un pedido en WhatsApp, envía una notificación al grupo de Telegram.

3. **Mantén un modelo de datos común**: Asegúrate de que la estructura de datos sea compatible entre ambos sistemas.

## Ejemplo de implementación de pedidos en WhatsApp

```javascript
// Estado de conversaciones
const userStates = new Map();

// Tipos de café disponibles
const TIPOS_CAFE = {
    '1': { nombre: 'Café Arábica Premium', precio: 50 },
    '2': { nombre: 'Café Arábica Estándar', precio: 40 },
    '3': { nombre: 'Café Orgánico', precio: 60 },
    '4': { nombre: 'Café Mezcla', precio: 35 },
};

// Función para guardar pedido
function guardarPedido(pedido) {
    const csvPath = '../data/pedidos_whatsapp.csv';
    const headers = 'fecha,hora,cliente,telefono,producto,cantidad,precio_unitario,total,direccion,estado,notas\n';
    
    if (!fs.existsSync(csvPath)) {
        fs.writeFileSync(csvPath, headers);
    }
    
    const row = `${pedido.fecha},${pedido.hora},${pedido.cliente},${pedido.telefono},${pedido.producto},${pedido.cantidad},${pedido.precio_unitario},${pedido.total},${pedido.direccion},${pedido.estado},${pedido.notas}\n`;
    fs.appendFileSync(csvPath, row);
}

client.on('message', async msg => {
    const chatId = msg.from;
    const message = msg.body.toLowerCase();
    
    // Obtener o inicializar estado del usuario
    if (!userStates.has(chatId)) {
        userStates.set(chatId, { step: 'inicio', data: {} });
    }
    
    const userState = userStates.get(chatId);
    
    // Máquina de estados para la conversación
    switch (userState.step) {
        case 'inicio':
            if (message === 'hola' || message === 'menu') {
                await msg.reply('¡Hola! Bienvenido al servicio de pedidos de café ☕\n\n' +
                    'Escribe 1 para hacer un pedido.');
                userState.step = 'menu_principal';
            }
            break;
            
        case 'menu_principal':
            if (message === '1') {
                userState.step = 'nombre_cliente';
                await msg.reply('Por favor, escribe tu nombre completo:');
            }
            break;
            
        // ... Resto de la implementación para los demás estados
    }
});
```

## Consideraciones adicionales

1. **Seguridad**: No almacenes información sensible en el código.

2. **Escalabilidad**: Considera migrar a una base de datos real (MySQL, MongoDB) si el volumen de pedidos crece.

3. **Mantenimiento**: La sesión de WhatsApp puede caducar. Implementa reintentos y notificaciones de error.

4. **Cumplimiento**: Asegúrate de cumplir con las políticas de WhatsApp y protección de datos.

## Próximos pasos

1. **Fase 1**: Implementar el bot básico de WhatsApp
2. **Fase 2**: Integrar con la base de datos existente
3. **Fase 3**: Implementar notificaciones cruzadas
4. **Fase 4**: Considerar migración a la API oficial si el volumen lo justifica

---

Para más información, consulta la documentación de [whatsapp-web.js](https://wwebjs.dev/).
