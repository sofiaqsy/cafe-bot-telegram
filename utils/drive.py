"""
Módulo para la interacción con Google Drive.
Permite subir archivos al Drive asociado a la cuenta de servicio.
"""

import logging
import io
import os
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
from config import DRIVE_EVIDENCIAS_ROOT_ID, DRIVE_EVIDENCIAS_COMPRAS_ID, DRIVE_EVIDENCIAS_VENTAS_ID

def get_drive_service():
    """Inicializa y retorna el servicio de Google Drive"""
    try:
        # Verificar que las credenciales estén configuradas
        if not GOOGLE_CREDENTIALS:
            logger.error("Credenciales de Google no configuradas")
            return None

        # Cargar credenciales desde la variable de entorno
        try:
            info = GOOGLE_CREDENTIALS
            # Si las credenciales son una ruta de archivo
            if os.path.exists(info):
                credentials = service_account.Credentials.from_service_account_file(info, scopes=SCOPES)
            # Si las credenciales son un JSON en string
            else:
                import json
                service_account_info = json.loads(info)
                credentials = service_account.Credentials.from_service_account_info(
                    service_account_info, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Error al cargar credenciales: {e}")
            return None

        # Construir servicio de Drive
        service = build('drive', 'v3', credentials=credentials)
        return service

    except Exception as e:
        logger.error(f"Error al inicializar servicio de Drive: {e}")
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
        service = get_drive_service()
        if not service:
            logger.error("No se pudo obtener el servicio de Drive")
            return None
        
        # Si no se especifica folder_id, usar la carpeta de evidencias raíz predeterminada
        if not folder_id:
            if DRIVE_EVIDENCIAS_ROOT_ID:
                folder_id = DRIVE_EVIDENCIAS_ROOT_ID
                logger.info(f"Usando carpeta raíz de evidencias: {folder_id}")
            
        # Preparar metadatos del archivo
        file_metadata = {'name': file_name}
        
        # Si se especificó una carpeta, añadirla a los metadatos
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # Preparar el contenido del archivo
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        
        # Subir el archivo
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink'
        ).execute()
        
        logger.info(f"Archivo subido exitosamente a Drive: {file.get('name')} (ID: {file.get('id')})")
        return file
    
    except HttpError as e:
        logger.error(f"Error HTTP al subir archivo a Drive: {e}")
        return None
    except Exception as e:
        logger.error(f"Error al subir archivo a Drive: {e}")
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
        service = get_drive_service()
        if not service:
            logger.error("No se pudo obtener el servicio de Drive")
            return None
        
        # Buscar si la carpeta ya existe
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
        
        results = service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        
        items = results.get('files', [])
        
        # Si la carpeta ya existe, devolver su ID
        if items:
            logger.info(f"Carpeta encontrada: {items[0].get('name')} (ID: {items[0].get('id')})")
            return items[0].get('id')
        
        # Si la carpeta no existe, crearla
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
        
        logger.info(f"Carpeta creada: {folder.get('name')} (ID: {folder.get('id')})")
        return folder.get('id')
    
    except HttpError as e:
        logger.error(f"Error HTTP al crear carpeta en Drive: {e}")
        return None
    except Exception as e:
        logger.error(f"Error al crear carpeta en Drive: {e}")
        return None

def setup_drive_folders():
    """
    Configura la estructura de carpetas necesaria en Google Drive
    
    Returns:
        bool: True si la configuración fue exitosa, False en caso contrario
    """
    try:
        # Nombre de la carpeta principal
        root_folder_name = "CafeBotEvidencias"
        
        # Crear carpeta principal si no existe
        root_id = create_folder_if_not_exists(root_folder_name)
        if not root_id:
            logger.error("No se pudo crear la carpeta principal en Drive")
            return False
        
        # Crear subcarpetas para compras y ventas
        compras_id = create_folder_if_not_exists("Compras", root_id)
        ventas_id = create_folder_if_not_exists("Ventas", root_id)
        
        if not compras_id or not ventas_id:
            logger.error("No se pudieron crear las subcarpetas en Drive")
            return False
        
        # Guardar los IDs de las carpetas en variables de entorno para uso futuro
        os.environ["DRIVE_EVIDENCIAS_ROOT_ID"] = root_id
        os.environ["DRIVE_EVIDENCIAS_COMPRAS_ID"] = compras_id
        os.environ["DRIVE_EVIDENCIAS_VENTAS_ID"] = ventas_id
        
        logger.info(f"Estructura de carpetas en Drive configurada correctamente. Root ID: {root_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error al configurar estructura de carpetas en Drive: {e}")
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
        service = get_drive_service()
        if not service:
            return None
        
        file = service.files().get(
            fileId=file_id,
            fields='webViewLink'
        ).execute()
        
        return file.get('webViewLink')
    
    except Exception as e:
        logger.error(f"Error al obtener enlace de archivo en Drive: {e}")
        return None