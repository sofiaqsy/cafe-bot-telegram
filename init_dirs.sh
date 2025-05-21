#!/bin/bash

# Script para inicializar directorios necesarios para el bot

echo "=== Inicializando directorios para CafeBot ==="

# Crear directorio raíz de uploads
mkdir -p uploads
echo "✅ Directorio uploads creado"

# Crear directorios para evidencias de compras y ventas
mkdir -p uploads/compras
mkdir -p uploads/ventas
echo "✅ Subdirectorios para evidencias creados"

# Verificar estructura
echo ""
echo "Estructura de directorios creada:"
find uploads -type d | sort

echo ""
echo "=== Inicialización completada ==="
echo "Los directorios están listos para almacenar archivos de evidencias."