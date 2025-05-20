#!/usr/bin/env python3
"""
Script para diagnosticar problemas con las credenciales de Google Drive.
Este script realiza pruebas exhaustivas para identificar problemas con las credenciales.
"""

import os
import json
import sys
import logging
import tempfile
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("credentials_check")

def validate_json(json_str):
    """Valida si una cadena es un JSON válido"""
    try:
        json_obj = json.loads(json_str)
        return True, json_obj
    except json.JSONDecodeError as e:
        return False, f"Error al decodificar JSON: {e}"

def check_google_credentials():
    """Verifica las credenciales de Google"""
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar si GOOGLE_CREDENTIALS está definido
    credentials = os.getenv("GOOGLE_CREDENTIALS")
    if not credentials:
        logger.error("❌ GOOGLE_CREDENTIALS no está definido en el archivo .env")
        logger.info("Añade la variable GOOGLE_CREDENTIALS al archivo .env con el contenido del archivo JSON de credenciales")
        return False

    # Verificar si es un archivo
    if os.path.exists(credentials):
        logger.info(f"✅ GOOGLE_CREDENTIALS contiene una ruta a un archivo: {credentials}")
        
        # Verificar si el archivo es legible
        try:
            with open(credentials, 'r') as f:
                cred_content = f.read()
            
            # Verificar si el contenido es un JSON válido
            is_valid, result = validate_json(cred_content)
            if is_valid:
                logger.info("✅ El archivo de credenciales contiene un JSON válido")
                return True
            else:
                logger.error(f"❌ El archivo de credenciales no contiene un JSON válido: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Error al leer el archivo de credenciales: {e}")
            return False
    
    # Si no es un archivo, verificar si es un JSON directo
    is_valid, result = validate_json(credentials)
    if is_valid:
        logger.info("✅ GOOGLE_CREDENTIALS contiene un JSON válido")
        
        # Verificar que el JSON tiene los campos necesarios
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            logger.error(f"❌ Faltan campos obligatorios en el JSON de credenciales: {', '.join(missing_fields)}")
            return False
        
        # Verificar si el private_key es válido
        if 'private_key' in result and '-----BEGIN PRIVATE KEY-----' in result['private_key']:
            logger.info("✅ La clave privada parece tener el formato correcto")
        else:
            logger.error("❌ La clave privada no tiene el formato correcto o está incompleta")
            return False
        
        # Si llegamos aquí, las credenciales parecen válidas
        return True
    else:
        # Si no es un JSON válido, verificar si está escapado incorrectamente
        try:
            # A veces las comillas simples o dobles del JSON se escapan incorrectamente
            fixed_json = credentials.replace('\\"', '"').replace("\\'", "'")
            is_valid, _ = validate_json(fixed_json)
            if is_valid:
                logger.error("❌ GOOGLE_CREDENTIALS contiene un JSON con escape incorrecto")
                logger.info("Corrige el formato de las credenciales en el archivo .env")
                return False
        except Exception:
            pass
        
        logger.error(f"❌ GOOGLE_CREDENTIALS no contiene un JSON válido ni es una ruta a un archivo: {result}")
        logger.info("Verifica que la variable GOOGLE_CREDENTIALS en el archivo .env contenga el JSON completo")
        
        # Si es muy largo, puede que esté truncado
        if len(credentials) > 1000:
            logger.info(f"La variable GOOGLE_CREDENTIALS es larga ({len(credentials)} caracteres)")
            logger.info("Si estás copiando el contenido del archivo JSON, asegúrate de copiarlo completo")
        
        return False

def test_create_temp_credentials_file():
    """Intenta crear un archivo temporal con las credenciales para depuración"""
    # Cargar variables de entorno
    load_dotenv()
    
    # Obtener credenciales
    credentials = os.getenv("GOOGLE_CREDENTIALS")
    if not credentials:
        logger.error("❌ GOOGLE_CREDENTIALS no está definido en el archivo .env")
        return False
    
    # Si ya es un archivo, no es necesario crear uno temporal
    if os.path.exists(credentials):
        logger.info(f"✅ Las credenciales ya están en un archivo: {credentials}")
        return True
    
    # Intentar validar el JSON
    is_valid, _ = validate_json(credentials)
    if not is_valid:
        logger.error("❌ No se puede crear un archivo temporal porque las credenciales no son un JSON válido")
        return False
    
    # Crear un archivo temporal
    try:
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write(credentials)
        temp_file.close()
        
        logger.info(f"✅ Archivo temporal de credenciales creado: {temp_file.name}")
        logger.info("Para solucionar el problema, agrega esta línea a tu archivo .env:")
        logger.info(f"GOOGLE_CREDENTIALS={temp_file.name}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error al crear archivo temporal: {e}")
        return False

def check_drive_folders():
    """Verifica la configuración de carpetas de Google Drive"""
    # Cargar variables de entorno
    load_dotenv()
    
    # Verificar si DRIVE_ENABLED está habilitado
    drive_enabled = os.getenv("DRIVE_ENABLED", "False").lower() in ("true", "1", "t")
    if not drive_enabled:
        logger.warning("⚠️ Google Drive está deshabilitado (DRIVE_ENABLED=False)")
        logger.info("Para habilitar Google Drive, añade la siguiente línea a tu archivo .env:")
        logger.info("DRIVE_ENABLED=True")
        return False
    
    # Verificar las carpetas
    folder_variables = {
        "DRIVE_EVIDENCIAS_ROOT_ID": os.getenv("DRIVE_EVIDENCIAS_ROOT_ID", ""),
        "DRIVE_EVIDENCIAS_COMPRAS_ID": os.getenv("DRIVE_EVIDENCIAS_COMPRAS_ID", ""),
        "DRIVE_EVIDENCIAS_VENTAS_ID": os.getenv("DRIVE_EVIDENCIAS_VENTAS_ID", "")
    }
    
    # Verificar si las carpetas están configuradas
    missing_folders = [var for var, val in folder_variables.items() if not val]
    if missing_folders:
        logger.warning(f"⚠️ Faltan IDs de carpetas: {', '.join(missing_folders)}")
        
        # Sugerir usar script de configuración
        logger.info("Para configurar automáticamente las carpetas, ejecuta el script check_drive.py:")
        logger.info("python check_drive.py")
        return False
    else:
        logger.info("✅ Todas las carpetas de Drive están configuradas")
        return True

def main():
    """Función principal"""
    print("\n======== DIAGNÓSTICO DE CREDENCIALES DE GOOGLE DRIVE ========\n")
    
    # Verificar credenciales
    creds_ok = check_google_credentials()
    if not creds_ok:
        print("\n⚠️ Se encontraron problemas con las credenciales de Google.")
        test_create_temp_credentials_file()
    
    # Verificar carpetas de Drive
    folders_ok = check_drive_folders()
    
    # Resumen
    print("\n======== RESUMEN DE DIAGNÓSTICO ========\n")
    if creds_ok:
        print("✅ Las credenciales de Google parecen estar correctamente configuradas.")
    else:
        print("❌ Hay problemas con las credenciales de Google.")
    
    if folders_ok:
        print("✅ Las carpetas de Google Drive están correctamente configuradas.")
    else:
        print("⚠️ Hay problemas con la configuración de carpetas de Google Drive.")
    
    # Proporcionar sugerencias finales
    if not creds_ok or not folders_ok:
        print("\nPasos recomendados para solucionar los problemas:")
        if not creds_ok:
            print("1. Verifica que el archivo de credenciales JSON sea válido")
            print("2. Asegúrate de que la variable GOOGLE_CREDENTIALS en el archivo .env contenga el JSON completo o la ruta al archivo")
        if not folders_ok:
            print("3. Ejecuta el script check_drive.py para configurar las carpetas automáticamente")
            print("4. Asegúrate de que DRIVE_ENABLED esté configurado como True en el archivo .env")
        
        print("\nUna vez realizados estos cambios, reinicia la aplicación para que surtan efecto.")
        return 1
    else:
        print("\n✅ La configuración de Google Drive está completa y debería funcionar correctamente.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
