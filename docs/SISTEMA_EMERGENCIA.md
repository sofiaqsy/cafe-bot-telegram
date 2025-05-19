# 🚨 SISTEMA DE EMERGENCIA PARA EVIDENCIAS DE PAGO

## ¿Qué ha cambiado?

El comando `/documento` presenta problemas técnicos que estamos solucionando. Mientras tanto, hemos implementado un **sistema alternativo** para que puedas seguir enviando tus evidencias de pago sin interrupciones.

## ✅ Cómo usar el nuevo sistema

1. Usa el comando `/evidencia` (en lugar de `/documento`)
2. Sigue las instrucciones en pantalla
3. Envía tu imagen con el formato solicitado

## 📝 Formato para enviar evidencias

Cuando envíes una evidencia de pago, incluye esta información en el mensaje:

```
Tipo: COMPRA o VENTA
ID: código de la operación
Descripción: detalles relevantes
```

Ejemplo:
```
Tipo: COMPRA
ID: C-2025-0042
Descripción: Pago a proveedor Juan Pérez, 50kg café
```

## 🔄 Actualización de comandos

Los administradores pueden actualizar la lista de comandos en BotFather usando:

```
/actualizar_comandos
```

Este comando está restringido a los administradores del sistema y actualizará automáticamente los comandos disponibles en el menú de Telegram.

---

## ⚙️ Detalles técnicos (para desarrolladores)

### Sistema de respaldos implementado

1. Registro de alta prioridad para el sistema de emergencia
2. Priorización del handler de emergencia sobre otros intentos
3. Detección de palabras clave para sugerir `/evidencia`
4. Compatibilidad con procesos manuales para los administradores

### Mejoras adicionales

- Comando para actualizar comandos en BotFather
- Sistema de logs mejorado
- Mejor manejo de errores