#!/bin/bash

# Script de deployment para agregar módulo de validación de clientes al bot de Telegram
echo "=========================================="
echo "🚀 DEPLOYMENT: Módulo de Validación de Clientes"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "bot.py" ]; then
    echo "❌ Error: No estás en el directorio cafe-bot-telegram"
    echo "   Por favor, navega al directorio correcto:"
    echo "   cd /Users/keylacusi/Desktop/OPEN IA/cafe-bots/cafe-bot-telegram"
    exit 1
fi

echo "📋 Características del nuevo módulo:"
echo "   ✅ Lista clientes por estado (Pendiente, Verificado, Rechazado, Prospecto)"
echo "   ✅ Muestra detalles completos del cliente"
echo "   ✅ Visualiza imagen de la cafetería si está disponible"
echo "   ✅ Permite cambiar el estado del cliente"
echo "   ✅ Integrado con Google Sheets"
echo ""

# Confirmar antes de continuar
read -p "¿Deseas desplegar el nuevo módulo? (s/n): " -n 1 -r
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

echo "💾 Creando commit..."
git commit -m "feat: Agregar módulo de validación de clientes

- Nuevo comando /clientes para gestionar validaciones
- Filtrado por estados: Pendiente, Verificado, Rechazado, Prospecto
- Visualización de detalles completos del cliente
- Soporte para ver imagen de la cafetería
- Actualización de estado integrada con Google Sheets
- Agregado al menú de ayuda"

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
    echo "✅ DEPLOYMENT COMPLETADO"
    echo "=========================================="
    echo ""
    echo "📱 Comandos disponibles en Telegram:"
    echo "   /clientes - Gestionar validación de clientes"
    echo "   /ayuda - Ver todos los comandos"
    echo ""
    echo "💡 Para monitorear en tiempo real:"
    echo "   heroku logs --tail --app cafe-bot-telegram"
else
    echo ""
    echo "❌ Error en el deployment"
    echo "   Revisa los logs para más detalles:"
    echo "   heroku logs --tail --app cafe-bot-telegram"
fi
