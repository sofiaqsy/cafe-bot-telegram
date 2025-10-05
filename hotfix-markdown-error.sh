#!/bin/bash

# Hotfix para error de parsing de Markdown en detalles de cliente
echo "=========================================="
echo "🔧 HOTFIX: Error de parsing en validación de clientes"
echo "=========================================="
echo ""

# Verificar directorio
if [ ! -f "bot.py" ]; then
    echo "❌ Error: No estás en el directorio cafe-bot-telegram"
    exit 1
fi

echo "📋 Problema detectado:"
echo "   Error: Can't parse entities en detalles del cliente"
echo "   Causa: Caracteres especiales no escapados en Markdown"
echo ""
echo "✅ Solución aplicada:"
echo "   - Función escape_markdown() para caracteres especiales"
echo "   - Escape correcto de todos los valores dinámicos"
echo "   - URLs sin escape para mantener funcionalidad"
echo ""

# Confirmar
read -p "¿Aplicar hotfix? (s/n): " -n 1 -r
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
git commit -m "hotfix: Escapar caracteres especiales en detalles de cliente

- Fix error 'Can't parse entities' en Telegram
- Agregar función escape_markdown()
- Escapar todos los valores dinámicos del cliente
- Mantener URLs sin escape para enlaces funcionales"

echo ""
echo "🚀 Desplegando a Heroku..."
git push heroku main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Hotfix aplicado exitosamente!"
    echo ""
    echo "📊 Verificando logs..."
    heroku logs --tail -n 20 --app cafe-bot-telegram | grep -E "(ERROR|clientes|parse)"
    echo ""
    echo "💡 Prueba el comando /clientes nuevamente"
else
    echo "❌ Error en deployment"
fi
