#!/bin/bash

# Hotfix v2 - Cambio completo a HTML para evitar errores de parsing
echo "=========================================="
echo "🔧 HOTFIX v2: Cambio a formato HTML en validación de clientes"
echo "=========================================="
echo ""

# Verificar directorio
if [ ! -f "bot.py" ]; then
    echo "❌ Error: No estás en el directorio cafe-bot-telegram"
    echo "   cd /Users/keylacusi/Desktop/OPEN IA/cafe-bots/cafe-bot-telegram"
    exit 1
fi

echo "📋 Cambios aplicados:"
echo "   ✅ Cambio completo de Markdown a HTML"
echo "   ✅ Función escape_html() para caracteres especiales"
echo "   ✅ Todos los parse_mode cambiados a 'HTML'"
echo "   ✅ Formato de mensajes usando etiquetas HTML"
echo ""

# Confirmar
read -p "¿Aplicar hotfix v2? (s/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Cancelado"
    exit 1
fi

# Git operations
echo ""
echo "📝 Aplicando cambios..."
git add handlers/clientes_validacion.py

echo "💾 Commit..."
git commit -m "hotfix(v2): Cambio completo a HTML en validación de clientes

- Cambio de parse_mode='Markdown' a parse_mode='HTML'
- Reemplazo de sintaxis Markdown (*texto*) por HTML (<b>texto</b>)
- Función escape_html() para caracteres especiales HTML
- Fix completo del error 'Can't parse entities'"

echo ""
echo "🚀 Desplegando a Heroku..."
git push heroku main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Hotfix v2 aplicado exitosamente!"
    echo ""
    
    # Esperar un momento para que se reinicie
    echo "⏳ Esperando reinicio del bot (10 segundos)..."
    sleep 10
    
    echo "📊 Verificando estado..."
    heroku ps --app cafe-bot-telegram
    
    echo ""
    echo "📝 Últimos logs (buscando errores)..."
    heroku logs --tail -n 30 --app cafe-bot-telegram | grep -E "(ERROR|WARN|clientes)" || echo "✅ No se encontraron errores recientes"
    
    echo ""
    echo "=========================================="
    echo "✅ HOTFIX COMPLETADO"
    echo "=========================================="
    echo ""
    echo "💡 Prueba nuevamente:"
    echo "   1. /clientes - Ver pendientes"
    echo "   2. Seleccionar un cliente"
    echo "   3. Verificar que muestre detalles sin error"
    echo ""
    echo "📱 El formato ahora usa HTML:"
    echo "   - Negritas: <b>texto</b>"
    echo "   - Código: <code>texto</code>"
    echo "   - Enlaces: <a href='url'>texto</a>"
else
    echo ""
    echo "❌ Error en deployment"
    echo "   Ejecuta: heroku logs --tail --app cafe-bot-telegram"
fi
