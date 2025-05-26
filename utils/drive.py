"""
Módulo para la interacción con Google Drive.
Permite subir archivos al Drive asociado a la cuenta de servicio.
"""

import logging
import io
import os
import traceback
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
from config import GOOGLE_CREDENTIALS

# Configurar logging
logger = logging.getLogger(__name__)

# Ámbitos (scopes) necesarios para Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/spreadsheets']

# IDs de las carpetas en Google Drive donde se guardarán las evidencias de pago
# Estos valores deben ser configurados según tu estructura de Drive
from config import (
    DRIVE_EVIDENCIAS_ROOT_ID, 
    DRIVE_EVIDENCIAS_COMPRAS_ID, 
    DRIVE_EVIDENCIAS_VENTAS_ID,
    DRIVE_EVIDENCIAS_ADELANTOS_ID,
    DRIVE_EVIDENCIAS_GASTOS_ID,
    DRIVE_EVIDENCIAS_CAPITALIZACION_ID
)

# Log de configuración al importar el módulo
logger.info("=== MÓDULO DRIVE.PY INICIALIZADO ===")
logger.info(f"DRIVE_EVIDENCIAS_ROOT_ID: {DRIVE_EVIDENCIAS_ROOT_ID or 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_COMPRAS_ID: {DRIVE_EVIDENCIAS_COMPRAS_ID or 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_VENTAS_ID: {DRIVE_EVIDENCIAS_VENTAS_ID or 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_ADELANTOS_ID: {DRIVE_EVIDENCIAS_ADELANTOS_ID or 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_GASTOS_ID: {DRIVE_EVIDENCIAS_GASTOS_ID or 'No configurado'}")
logger.info(f"DRIVE_EVIDENCIAS_CAPITALIZACION_ID: {DRIVE_EVIDENCIAS_CAPITALIZACION_ID or 'No configurado'}")

def get_drive_service():
    """Inicializa y retorna el servicio de Google Drive"""
    try:
        logger.info("Inicializando servicio de Google Drive...")
        # Verificar que las credenciales estén configuradas
        if not GOOGLE_CREDENTIALS:
            logger.error("Credenciales de Google no configuradas")
            return None

        # Cargar credenciales desde la variable de entorno
        try:
            info = GOOGLE_CREDENTIALS
            # Si las credenciales son una ruta de archivo
            if os.path.exists(info):
                logger.info(f"Cargando credenciales desde archivo: {info}")
                credentials = service_account.Credentials.from_service_account_file(info, scopes=SCOPES)
            # Si las credenciales son un JSON en string
            else:
                logger.info("Cargando credenciales desde JSON en variable de entorno")
                import json
                service_account_info = json.loads(info)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=SCOPES)
            
            logger.info("Credenciales cargadas correctamente")
        except Exception as e:
            logger.error(f"Error al cargar credenciales: {e}")
            logger.error(traceback.format_exc())
            return None

        # Construir servicio de Drive
        service = build('drive', 'v3', credentials=credentials)
        logger.info("Servicio de Google Drive inicializado correctamente")
        return service

    except Exception as e:
        logger.error(f"Error al inicializar servicio de Drive: {e}")
        logger.error(traceback.format_exc())
        return None

def upload_file_to_drive(file_bytes, file_name, mime_type="image/jpeg", folder_id=None):
    """
    Sube un archivo a Google Drive
    
    Args:
        file_bytes: Bytes del archivo a subir
        file_name: Nombre que tendrá el archivo en Drive
        mime_type: Tipo MIME del archivo
        folder_id: ID de la carpeta donde se guardará (opcional)
    
    Returns:
        dict: Información del archivo subido o None si hay error
    """
    try:
        logger.info(f"=== SUBIENDO ARCHIVO A DRIVE: {file_name} ===")
        logger.info(f"Tipo MIME: {mime_type}")
        logger.info(f"Tamaño del archivo: {len(file_bytes)} bytes")
        logger.info(f"Carpeta especificada: {folder_id or 'No especificada'}")
        
        service = get_drive_service()
        if not service:
            logger.error("No se pudo obtener el servicio de Drive")
            return None
        
        # Si no se especifica folder_id, usar la carpeta de evidencias raíz predeterminada
        if not folder_id:
            if DRIVE_EVIDENCIAS_ROOT_ID:
                folder_id = DRIVE_EVIDENCIAS_ROOT_ID
                logger.info(f"Usando carpeta raíz de evidencias: {folder_id}")
            else:
                logger.warning("DRIVE_EVIDENCIAS_ROOT_ID no está configurado, el archivo se subirá sin carpeta específica")
        
        # Preparar metadatos del archivo
        file_metadata = {'name': file_name}
        
        # Si se especificó una carpeta, añadirla a los metadatos
        if folder_id:
            file_metadata['parents'] = [folder_id]
            logger.info(f"Archivo será guardado en carpeta con ID: {folder_id}")
        else:
            logger.warning("El archivo se subirá sin especificar carpeta")
        
        # Preparar el contenido del archivo
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        
        # Subir el archivo
        logger.info("Iniciando subida a Google Drive...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        logger.info(f"¡Archivo subido exitosamente a Drive!")
        logger.info(f"Nombre: {file.get('name')}")
        logger.info(f"ID: {file.get('id')}")
        logger.info(f"Enlace: {file.get('webViewLink')}")
        return file
    
    except HttpError as e:
        logger.error(f"Error HTTP al subir archivo a Drive: {e}")
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"Error al subir archivo a Drive: {e}")
        logger.error(traceback.format_exc())
        return None

def create_folder_if_not_exists(folder_name, parent_folder_id=None):
    """
    Crea una carpeta en Google Drive si no existe
    
    Args:
        folder_name: Nombre de la carpeta a crear
        parent_folder_id: ID de la carpeta padre (opcional)
        
    Returns:
        str: ID de la carpeta creada o encontrada, None si hay error
    """
    try:
        logger.info(f"Buscando o creando carpeta '{folder_name}'")
        if parent_folder_id:
            logger.info(f"Carpeta padre especificada: {parent_folder_id}")
        
        service = get_drive_service()
        if not service:
            logger.error("No se pudo obtener el servicio de Drive")
            return None
        
        # Buscar si la carpeta ya existe
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
        
        logger.info(f"Ejecutando búsqueda con query: {query}")
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        # Si la carpeta ya existe, devolver su ID
        if items:
            logger.info(f"Carpeta existente encontrada: {items[0].get('name')} (ID: {items[0].get('id')})")
            return items[0].get('id')
        
        # Si la carpeta no existe, crearla
        logger.info(f"Carpeta no encontrada. Creando carpeta '{folder_name}'...")
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_folder_id:
            folder_metadata['parents'] = [parent_folder_id]
        
        folder = service.files().create(
            body=folder_metadata,
            fields='id, name'
        ).execute()
        
        logger.info(f"Carpeta creada exitosamente: {folder.get('name')} (ID: {folder.get('id')})")
        return folder.get('id')
    
    except HttpError as e:
        logger.error(f"Error HTTP al crear carpeta en Drive: {e}")
        logger.error(traceback.format_exc())
        return None
    except Exception as e:
        logger.error(f"Error al crear carpeta en Drive: {e}")
        logger.error(traceback.format_exc())
        return None

def setup_drive_folders():
    """
    Configura la estructura de carpetas necesaria en Google Drive
    
    Returns:
        bool: True si la configuración fue exitosa, False en caso contrario
    """
    try:
        logger.info("=== CONFIGURANDO ESTRUCTURA DE CARPETAS EN GOOGLE DRIVE ===")
        
        # Nombre de la carpeta principal
        root_folder_name = "CafeBotEvidencias"
        
        # Crear carpeta principal si no existe
        logger.info(f"Verificando carpeta principal: {root_folder_name}")
        root_id = create_folder_if_not_exists(root_folder_name)
        if not root_id:
            logger.error("No se pudo crear la carpeta principal en Drive")
            return False
        
        # Crear subcarpetas para compras y ventas
        logger.info("Verificando subcarpeta para Compras")
        compras_id = create_folder_if_not_exists("Compras", root_id)
        
        logger.info("Verificando subcarpeta para Ventas")
        ventas_id = create_folder_if_not_exists("Ventas", root_id)
        
        # Crear subcarpetas para adelantos, gastos y capitalización
        logger.info("Verificando subcarpeta para Adelantos")
        adelantos_id = create_folder_if_not_exists("Adelantos", root_id)
        
        logger.info("Verificando subcarpeta para Gastos")
        gastos_id = create_folder_if_not_exists("Gastos", root_id)
        
        logger.info("Verificando subcarpeta para Capitalización")
        capitalizacion_id = create_folder_if_not_exists("Capitalizacion", root_id)
        
        # Verificar que todas las carpetas se crearon correctamente
        if not (compras_id and ventas_id and adelantos_id and gastos_id and capitalizacion_id):
            logger.error("No se pudieron crear todas las subcarpetas en Drive")
            return False
        
        # Guardar los IDs de las carpetas en variables de entorno para uso futuro
        from config import update_env_var
        
        update_env_var("DRIVE_EVIDENCIAS_ROOT_ID", root_id)
        update_env_var("DRIVE_EVIDENCIAS_COMPRAS_ID", compras_id)
        update_env_var("DRIVE_EVIDENCIAS_VENTAS_ID", ventas_id)
        update_env_var("DRIVE_EVIDENCIAS_ADELANTOS_ID", adelantos_id)
        update_env_var("DRIVE_EVIDENCIAS_GASTOS_ID", gastos_id)
        update_env_var("DRIVE_EVIDENCIAS_CAPITALIZACION_ID", capitalizacion_id)
        
        logger.info("=== ESTRUCTURA DE CARPETAS EN DRIVE CONFIGURADA CORRECTAMENTE ===")
        logger.info(f"Carpeta principal: {root_folder_name} (ID: {root_id})")
        logger.info(f"Subcarpeta Compras ID: {compras_id}")
        logger.info(f"Subcarpeta Ventas ID: {ventas_id}")
        logger.info(f"Subcarpeta Adelantos ID: {adelantos_id}")
        logger.info(f"Subcarpeta Gastos ID: {gastos_id}")
        logger.info(f"Subcarpeta Capitalización ID: {capitalizacion_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error al configurar estructura de carpetas en Drive: {e}")
        logger.error(traceback.format_exc())
        return False

def get_file_link(file_id):
    """
    Obtiene el enlace de visualización de un archivo en Google Drive
    
    Args:
        file_id: ID del archivo en Google Drive
        
    Returns:
        str: URL para ver el archivo, None si hay error
    """
    try:
        logger.info(f"Obteniendo enlace para archivo con ID: {file_id}")
        service = get_drive_service()
        if not service:
            return None
        
        file = service.files().get(
            fileId=file_id,
            fields='webViewLink'
        ).execute()
        
        link = file.get('webViewLink')
        logger.info(f"Enlace obtenido: {link}")
        return link
    
    except Exception as e:
        logger.error(f"Error al obtener enlace de archivo en Drive: {e}")
        logger.error(traceback.format_exc())
        return None