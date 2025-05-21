#!/bin/bash

# Script para verificar configuración de Google Drive en Heroku

echo "=== Verificando configuración de Google Drive en Heroku ==="

# Verificar DRIVE_ENABLED
DRIVE_ENABLED=$(heroku config:get DRIVE_ENABLED)
if [ "$DRIVE_ENABLED" = "true" ] || [ "$DRIVE_ENABLED" = "TRUE" ] || [ "$DRIVE_ENABLED" = "1" ]; then
    echo "✅ DRIVE_ENABLED está configurado como: $DRIVE_ENABLED"
else
    echo "❌ DRIVE_ENABLED no está activado. Activándolo..."
    heroku config:set DRIVE_ENABLED=true
    echo "✅ DRIVE_ENABLED ha sido configurado como: true"
fi

# Verificar GOOGLE_CREDENTIALS
GOOGLE_CREDS=$(heroku config:get GOOGLE_CREDENTIALS | wc -c)
if [ "$GOOGLE_CREDS" -gt 100 ]; then
    echo "✅ GOOGLE_CREDENTIALS está configurado (tiene más de 100 caracteres)"
else
    echo "❌ GOOGLE_CREDENTIALS no está configurado o es muy corto"
    echo "Por favor, configura GOOGLE_CREDENTIALS con el contenido del archivo JSON de credenciales de servicio:"
    echo "heroku config:set GOOGLE_CREDENTIALS='$(cat your-credentials.json)'"
fi

# Verificar SPREADSHEET_ID
SPREADSHEET_ID=$(heroku config:get SPREADSHEET_ID)
if [ -n "$SPREADSHEET_ID" ]; then
    echo "✅ SPREADSHEET_ID está configurado: $SPREADSHEET_ID"
else
    echo "❌ SPREADSHEET_ID no está configurado"
    echo "Por favor, configura SPREADSHEET_ID con el ID de tu hoja de Google Sheets:"
    echo "heroku config:set SPREADSHEET_ID='tu-spreadsheet-id'"
fi

# Verificar ID de carpetas de Drive
ROOT_ID=$(heroku config:get DRIVE_EVIDENCIAS_ROOT_ID)
COMPRAS_ID=$(heroku config:get DRIVE_EVIDENCIAS_COMPRAS_ID)
VENTAS_ID=$(heroku config:get DRIVE_EVIDENCIAS_VENTAS_ID)

if [ -n "$ROOT_ID" ] && [ -n "$COMPRAS_ID" ] && [ -n "$VENTAS_ID" ]; then
    echo "✅ Las carpetas de Drive están configuradas:"
    echo "  DRIVE_EVIDENCIAS_ROOT_ID: $ROOT_ID"
    echo "  DRIVE_EVIDENCIAS_COMPRAS_ID: $COMPRAS_ID"
    echo "  DRIVE_EVIDENCIAS_VENTAS_ID: $VENTAS_ID"
else
    echo "⚠️ No todas las carpetas de Drive están configuradas."
    echo "Esto no es un problema, el bot creará las carpetas automáticamente al iniciar"
    echo "y configurará las variables de entorno correspondientes en Heroku."
fi

echo "=== Verificación completa ==="
echo ""
echo "Si hay problemas con la configuración, puedes solucionarlos manualmente con:"
echo "heroku config:set VARIABLE=valor"
echo ""
echo "Para verificar la configuración completa, usa:"
echo "heroku config"