#!/bin/bash

# Script de deployment para módulo de validación de clientes con vista por defecto de pendientes
echo "=========================================="
echo "🚀 DEPLOYMENT: Módulo de Validación de Clientes v1.1"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "bot.py" ]; then
    echo "❌ Error: No estás en el directorio cafe-bot-telegram"
    echo "   Por favor, navega al directorio correcto:"
    echo "   cd /Users/keylacusi/Desktop/OPEN IA/cafe-bots/cafe-bot-telegram"
    exit 1
fi

echo "📋 Actualización v1.1 - Cambios:"
echo "   ✅ Por defecto muestra clientes PENDIENTES"
echo "   ✅ Vista directa de pendientes al ejecutar /clientes"
echo "   ✅ Botón para cambiar a otros estados"
echo "   ✅ Mejor flujo de trabajo para validación"
echo ""

# Confirmar antes de continuar
read -p "¿Deseas desplegar estos cambios? (s/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo "❌ Deployment cancelado"
    exit 1
fi

echo ""
echo "📝 Agregando cambios a git..."
git add handlers/clientes_validacion.py
git add handlers/start.py
git add bot.py
git add CLIENTES_VALIDACION.md

echo "💾 Creando commit..."
git commit -m "update: Clientes pendientes por defecto en validación

- Muestra directamente clientes pendientes al ejecutar /clientes
- Si no hay pendientes, muestra el menú de filtros
- Botón 'Ver otros estados' para cambiar filtro
- Mejora el flujo de validación diaria"

echo ""
echo "🚀 Desplegando a Heroku..."
git push heroku main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Deployment exitoso!"
    echo ""
    echo "📊 Verificando estado de la aplicación..."
    heroku ps --app cafe-bot-telegram
    
    echo ""
    echo "📝 Mostrando logs recientes..."
    heroku logs --tail -n 30 --app cafe-bot-telegram
    
    echo ""
    echo "=========================================="
    echo "✅ ACTUALIZACIÓN COMPLETADA - v1.1"
    echo "=========================================="
    echo ""
    echo "📱 Flujo actualizado:"
    echo "   1. /clientes → Muestra pendientes directamente"
    echo "   2. Seleccionar cliente → Ver detalles + imagen"
    echo "   3. Cambiar estado → Verificado/Rechazado/Prospecto"
    echo ""
    echo "💡 Para monitorear en tiempo real:"
    echo "   heroku logs --tail --app cafe-bot-telegram"
else
    echo ""
    echo "❌ Error en el deployment"
    echo "   Revisa los logs para más detalles:"
    echo "   heroku logs --tail --app cafe-bot-telegram"
fi
