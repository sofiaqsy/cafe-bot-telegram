#!/usr/bin/env python3
"""
Script de prueba local para el módulo de validación de clientes
Ejecutar desde el directorio cafe-bot-telegram
"""

import os
import sys
from pathlib import Path

# Agregar el directorio actual al path
sys.path.insert(0, str(Path(__file__).parent))

# Configurar variables de entorno de prueba si no existen
if not os.getenv('TELEGRAM_BOT_TOKEN'):
    print("⚠️ TELEGRAM_BOT_TOKEN no configurado, usando modo de prueba")
    os.environ['TELEGRAM_BOT_TOKEN'] = 'test-token'

if not os.getenv('GOOGLE_SPREADSHEET_ID'):
    print("⚠️ GOOGLE_SPREADSHEET_ID no configurado")
    print("   El módulo necesita acceso a Google Sheets para funcionar")
    sys.exit(1)

# Importar el módulo
try:
    from handlers.clientes_validacion import (
        obtener_clientes,
        ESTADOS_CLIENTE,
        actualizar_estado_cliente
    )
    print("✅ Módulo importado correctamente")
except Exception as e:
    print(f"❌ Error importando módulo: {e}")
    sys.exit(1)

# Función de prueba
def test_obtener_clientes():
    """Prueba la obtención de clientes"""
    print("\n🔍 Probando obtención de clientes...")
    print("-" * 40)
    
    # Probar obtención de todos los clientes
    print("\n1. Obteniendo TODOS los clientes:")
    todos = obtener_clientes()
    if todos:
        print(f"   ✅ Se encontraron {len(todos)} cliente(s)")
        for cliente in todos[:3]:  # Mostrar máximo 3
            print(f"      - {cliente['empresa'] or 'Sin empresa'} ({cliente['estado']})")
    else:
        print("   ⚠️ No se encontraron clientes")
    
    # Probar filtro por estado
    print("\n2. Filtrando por estado:")
    for estado in ['Pendiente', 'Verificado', 'Rechazado', 'Prospecto']:
        clientes = obtener_clientes(filtro_estado=estado)
        print(f"   {ESTADOS_CLIENTE[estado]}: {len(clientes) if clientes else 0} cliente(s)")
        
        # Mostrar detalles del primer cliente pendiente
        if estado == 'Pendiente' and clientes:
            print("\n   📋 Detalle del primer cliente pendiente:")
            cliente = clientes[0]
            print(f"      ID: {cliente['id']}")
            print(f"      Empresa: {cliente['empresa'] or 'N/A'}")
            print(f"      Contacto: {cliente['contacto'] or 'N/A'}")
            print(f"      WhatsApp: {cliente['whatsapp'] or 'N/A'}")
            print(f"      Distrito: {cliente['distrito'] or 'N/A'}")
            print(f"      Estado: {cliente['estado']}")
            if cliente.get('imagen_url'):
                print(f"      Imagen: {cliente['imagen_url'][:50]}...")

def test_flujo_validacion():
    """Simula el flujo de validación"""
    print("\n🔄 Simulando flujo de validación...")
    print("-" * 40)
    
    # Obtener clientes pendientes
    pendientes = obtener_clientes(filtro_estado='Pendiente')
    
    if not pendientes:
        print("⚠️ No hay clientes pendientes para validar")
        return
    
    print(f"✅ {len(pendientes)} cliente(s) pendiente(s) de validación")
    print("\nFlujo esperado:")
    print("1. Usuario ejecuta /clientes")
    print(f"2. Bot muestra {len(pendientes)} cliente(s) pendiente(s)")
    print("3. Usuario selecciona un cliente")
    print("4. Bot muestra detalles + imagen (si existe)")
    print("5. Usuario cambia estado a Verificado/Rechazado/Prospecto")
    print("6. Bot actualiza en Google Sheets")
    
    # Mostrar ejemplo de cambio de estado
    cliente = pendientes[0]
    print(f"\n📝 Ejemplo con cliente: {cliente['empresa'] or cliente['contacto']}")
    print(f"   Estado actual: {cliente['estado']}")
    print("   Estados disponibles para cambiar:")
    for estado in ['Verificado', 'Rechazado', 'Prospecto']:
        if estado != cliente['estado']:
            print(f"      → {ESTADOS_CLIENTE[estado]}")

def main():
    """Función principal de prueba"""
    print("=" * 50)
    print("🧪 PRUEBA DEL MÓDULO DE VALIDACIÓN DE CLIENTES")
    print("=" * 50)
    
    try:
        # Verificar conexión con Google Sheets
        from utils.sheets import get_sheet_service
        service = get_sheet_service()
        if service:
            print("✅ Conexión con Google Sheets establecida")
        else:
            print("❌ No se pudo conectar con Google Sheets")
            print("   Verifica las credenciales y el SPREADSHEET_ID")
            return
    except Exception as e:
        print(f"❌ Error verificando conexión: {e}")
        return
    
    # Ejecutar pruebas
    test_obtener_clientes()
    test_flujo_validacion()
    
    print("\n" + "=" * 50)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 50)
    print("\n💡 Si todo se ve bien, ejecuta:")
    print("   ./deploy-clientes-v1.1.sh")

if __name__ == "__main__":
    main()
