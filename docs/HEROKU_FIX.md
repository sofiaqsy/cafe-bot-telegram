# Corrección para Heroku App

Esta carpeta contiene los archivos necesarios para corregir el problema del comando `/documento` en el bot desplegado en Heroku.

## 🔍 Problema identificado

Revisando los logs de Heroku, se detectó que el bot está utilizando `heroku_app.py` como punto de entrada en lugar de `bot.py`. Sin embargo, el archivo `heroku_app.py` no incluía ninguna referencia al módulo de documentos, lo que explica por qué el comando `/documento` no estaba funcionando.

## 🛠️ Solución implementada

Se ha actualizado el archivo `heroku_app.py` para:

1. **Intentar importar el módulo documents original** para usar su funcionalidad si está disponible.

2. **Implementar un handler simplificado directamente en el archivo** como respaldo, que:
   - Responde al comando `/documento` con instrucciones claras
   - Procesa fotos que parecen evidencias de pago según su descripción
   - Almacena las evidencias en el directorio de uploads
   - Extrae automáticamente información de las descripciones (tipo e ID)

3. **Añadir un comando `/test_bot`** que muestra el estado del sistema.

## 💡 Funcionamiento

La solución sigue un enfoque de dos niveles:

1. **Si el módulo documents está disponible:**
   - Se importa y registra normalmente
   - Utiliza toda la funcionalidad del módulo original

2. **Si el módulo documents no está disponible o falla:**
   - Se registra un handler simple para `/documento` directamente en `heroku_app.py`
   - Se registra un detector de fotos que parecen evidencias
   - El sistema funciona sin depender del módulo original

## 🚀 Ventajas

- **No requiere cambios estructurales**: La solución se integra directamente en el flujo existente
- **Independiente del módulo documents**: Funciona incluso si el módulo original falla o no existe
- **Experiencia de usuario consistente**: Los usuarios reciben instrucciones claras y confirmaciones

## 📝 Notas importantes

1. Las evidencias se guardan en el directorio definido por la variable de entorno `UPLOADS_FOLDER`
2. Se registran logs detallados para facilitar el diagnóstico y seguimiento
3. Esta solución es compatible con la versión anterior y no afecta a otros comandos

## 🔜 Próximos pasos

Una vez implementada esta solución, se recomienda:

1. Verificar los logs para confirmar que el comando `/documento` está funcionando
2. Investigar por qué el módulo documents no se está registrando correctamente
3. Considera unificar los archivos `bot.py` y `heroku_app.py` para evitar divergencias