#!/usr/bin/env python3
"""
Script para verificar y configurar Google Drive.
Este script comprueba que las credenciales de Google Drive estén correctamente configuradas
y muestra información sobre la configuración actual.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from utils.drive import get_drive_service, setup_drive_folders

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("drive_check")

def check_google_drive_config():
    """
    Verifica la configuración de Google Drive y muestra información útil.
    """
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar si está habilitado Google Drive
    drive_enabled = os.getenv("DRIVE_ENABLED", "False").lower() in ("true", "1", "t")
    if not drive_enabled:
        logger.warning("Google Drive no está habilitado. Configura DRIVE_ENABLED=True en el archivo .env")
        logger.info("Para habilitar Google Drive, añade la siguiente línea a tu archivo .env:")
        logger.info("DRIVE_ENABLED=True")
        return False
    
    # Verificar credenciales de Google
    google_credentials = os.getenv("GOOGLE_CREDENTIALS")
    if not google_credentials:
        logger.error("No se han configurado las credenciales de Google (GOOGLE_CREDENTIALS)")
        logger.info("Sigue estas instrucciones para configurar GOOGLE_CREDENTIALS:")
        logger.info("1. Ve a la consola de Google Cloud: https://console.cloud.google.com/")
        logger.info("2. Crea un proyecto o selecciona uno existente")
        logger.info("3. Habilita la API de Google Drive: APIs & Services > Library > Google Drive API")
        logger.info("4. Crea una cuenta de servicio: IAM & Admin > Service Accounts")
        logger.info("5. Crea una clave para esta cuenta (JSON)")
        logger.info("6. Copia el contenido del archivo JSON descargado")
        logger.info("7. Añade a tu archivo .env: GOOGLE_CREDENTIALS='contenido_json_aquí'")
        return False
    
    # Verificar si se puede inicializar el servicio de Drive
    drive_service = get_drive_service()
    if not drive_service:
        logger.error("No se pudo inicializar el servicio de Google Drive")
        logger.info("Verifica que las credenciales sean correctas y tengan los permisos necesarios")
        return False
    
    logger.info("✅ Servicio de Google Drive inicializado correctamente")
    
    # Verificar IDs de carpetas
    drive_evidencias_root_id = os.getenv("DRIVE_EVIDENCIAS_ROOT_ID", "")
    drive_evidencias_compras_id = os.getenv("DRIVE_EVIDENCIAS_COMPRAS_ID", "")
    drive_evidencias_ventas_id = os.getenv("DRIVE_EVIDENCIAS_VENTAS_ID", "")
    
    if not drive_evidencias_root_id or not drive_evidencias_compras_id or not drive_evidencias_ventas_id:
        logger.warning("No se han configurado los IDs de carpetas de Drive")
        
        # Preguntar si desea configurar las carpetas automáticamente
        print("\n¿Deseas configurar las carpetas de Drive automáticamente? (s/n): ", end="")
        respuesta = input().strip().lower()
        
        if respuesta in ["s", "si", "sí", "y", "yes"]:
            logger.info("Configurando carpetas de Drive automáticamente...")
            if setup_drive_folders():
                # Las variables de entorno se actualizan en memoria, mostrar los nuevos valores
                logger.info("✅ Carpetas configuradas correctamente")
                logger.info(f"DRIVE_EVIDENCIAS_ROOT_ID: {os.getenv('DRIVE_EVIDENCIAS_ROOT_ID')}")
                logger.info(f"DRIVE_EVIDENCIAS_COMPRAS_ID: {os.getenv('DRIVE_EVIDENCIAS_COMPRAS_ID')}")
                logger.info(f"DRIVE_EVIDENCIAS_VENTAS_ID: {os.getenv('DRIVE_EVIDENCIAS_VENTAS_ID')}")
                
                # Instrucciones para actualizar el archivo .env
                print("\nPara mantener esta configuración, añade las siguientes líneas a tu archivo .env:")
                print(f"DRIVE_EVIDENCIAS_ROOT_ID={os.getenv('DRIVE_EVIDENCIAS_ROOT_ID')}")
                print(f"DRIVE_EVIDENCIAS_COMPRAS_ID={os.getenv('DRIVE_EVIDENCIAS_COMPRAS_ID')}")
                print(f"DRIVE_EVIDENCIAS_VENTAS_ID={os.getenv('DRIVE_EVIDENCIAS_VENTAS_ID')}")
                return True
            else:
                logger.error("No se pudieron configurar las carpetas automáticamente")
                return False
        else:
            logger.info("Para configurar manualmente, sigue estos pasos:")
            logger.info("1. Crea una carpeta en Google Drive para las evidencias")
            logger.info("2. Dentro de esta carpeta, crea dos subcarpetas: 'Compras' y 'Ventas'")
            logger.info("3. Obtén los IDs de las carpetas (de la URL: https://drive.google.com/drive/folders/ID_CARPETA)")
            logger.info("4. Añade a tu archivo .env:")
            logger.info("   DRIVE_EVIDENCIAS_ROOT_ID=id_carpeta_principal")
            logger.info("   DRIVE_EVIDENCIAS_COMPRAS_ID=id_carpeta_compras")
            logger.info("   DRIVE_EVIDENCIAS_VENTAS_ID=id_carpeta_ventas")
            return False
    else:
        logger.info("✅ IDs de carpetas configurados correctamente")
        logger.info(f"DRIVE_EVIDENCIAS_ROOT_ID: {drive_evidencias_root_id}")
        logger.info(f"DRIVE_EVIDENCIAS_COMPRAS_ID: {drive_evidencias_compras_id}")
        logger.info(f"DRIVE_EVIDENCIAS_VENTAS_ID: {drive_evidencias_ventas_id}")
        return True

def main():
    """Función principal"""
    print("\n======== VERIFICACIÓN DE CONFIGURACIÓN DE GOOGLE DRIVE ========\n")
    
    if check_google_drive_config():
        print("\n✅ La configuración de Google Drive está completa y funcionando correctamente.")
        return 0
    else:
        print("\n❌ Hay problemas con la configuración de Google Drive.")
        print("Soluciona los problemas indicados y vuelve a ejecutar este script.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
