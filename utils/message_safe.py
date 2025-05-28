import logging

# Configurar logging
logger = logging.getLogger(__name__)

def safe_markdown_message(message_text):
    """
    Asegura que un mensaje Markdown no tenga problemas de entidades.
    
    Verifica y corrige problemas comunes en mensajes Markdown que podrían
    causar errores del tipo 'can't find end of the entity'.
    
    Args:
        message_text (str): El texto del mensaje con formato Markdown
        
    Returns:
        str: El texto corregido para un envío seguro
    """
    if not message_text:
        return ""
    
    # Lista de caracteres especiales de Markdown que pueden causar problemas
    markdown_chars = ['*', '_', '`', '[', ']']
    
    # Verificar asteriscos (* para negrita o cursiva)
    asterisks_count = message_text.count('*')
    if asterisks_count % 2 != 0:
        # Número impar de asteriscos - problema potencial
        logger.warning(f"Número impar de asteriscos en mensaje: {asterisks_count}")
        # Escapar todos los asteriscos para prevenir errores
        message_text = message_text.replace('*', '\\*')
    
    # Verificar guiones bajos (_ para cursiva)
    underscores_count = message_text.count('_')
    if underscores_count % 2 != 0:
        # Número impar de guiones bajos - problema potencial
        logger.warning(f"Número impar de guiones bajos en mensaje: {underscores_count}")
        # Escapar todos los guiones bajos para prevenir errores
        message_text = message_text.replace('_', '\\_')
    
    # Verificar acentos graves (` para código)
    backticks_count = message_text.count('`')
    if backticks_count % 2 != 0:
        # Número impar de acentos graves - problema potencial
        logger.warning(f"Número impar de acentos graves en mensaje: {backticks_count}")
        # Escapar todos los acentos graves para prevenir errores
        message_text = message_text.replace('`', '\\`')
    
    # Verificar corchetes y paréntesis para enlaces
    brackets_open = message_text.count('[')
    brackets_close = message_text.count(']')
    parenthesis_open = message_text.count('(')
    parenthesis_close = message_text.count(')')
    
    if brackets_open != brackets_close or parenthesis_open != parenthesis_close:
        logger.warning(f"Desequilibrio en corchetes o paréntesis: []{brackets_open}:{brackets_close} (){parenthesis_open}:{parenthesis_close}")
        # Escapar todos los corchetes y paréntesis para prevenir errores
        message_text = message_text.replace('[', '\\[')
        message_text = message_text.replace(']', '\\]')
        message_text = message_text.replace('(', '\\(')
        message_text = message_text.replace(')', '\\)')
    
    return message_text

def fix_message_entities(message_text):
    """
    Función auxiliar para corregir entidades en mensajes.
    
    Esta función analiza el texto en busca de posibles problemas de formato
    en las entidades de Telegram e intenta corregirlos.
    
    Args:
        message_text (str): El texto del mensaje a corregir
        
    Returns:
        str: El texto corregido
    """
    if not message_text:
        return ""
    
    # Intentar identificar caracteres problemáticos con UTF-8 y reemplazarlos
    try:
        # Re-encode para detectar problemas
        encoded = message_text.encode('utf-8', errors='replace')
        decoded = encoded.decode('utf-8', errors='replace')
        
        # Si hay diferencia, hay caracteres problemáticos
        if decoded != message_text:
            logger.warning("Detectados caracteres problemáticos en el mensaje")
            message_text = decoded
    except Exception as e:
        logger.error(f"Error al verificar codificación: {e}")
    
    # Verificar longitud máxima (Telegram tiene un límite de 4096 caracteres)
    if len(message_text) > 4000:  # Usar 4000 como precaución
        logger.warning(f"Mensaje demasiado largo: {len(message_text)} caracteres, truncando")
        message_text = message_text[:3997] + "..."
    
    return message_text

def send_safe_message(update, text, parse_mode=None, **kwargs):
    """
    Envía un mensaje con procesamiento seguro para evitar errores de entidades.
    
    Args:
        update: Update de Telegram
        text: Texto del mensaje
        parse_mode: Modo de parseo (Markdown, HTML, etc.)
        **kwargs: Argumentos adicionales para reply_text
        
    Returns:
        Future: El resultado de reply_text
    """
    # Aplicar correcciones según el modo de parseo
    if parse_mode == "Markdown" or parse_mode == "MarkdownV2":
        text = safe_markdown_message(text)
    
    # Aplicar correcciones generales
    text = fix_message_entities(text)
    
    # Enviar mensaje con try-except para manejar cualquier error restante
    try:
        return update.message.reply_text(text=text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        logger.error(f"Error al enviar mensaje: {e}")
        # Si falla, intentar enviar sin formato
        try:
            return update.message.reply_text(
                text=f"Error de formato en el mensaje original. Versión sin formato:\n\n{text}", 
                parse_mode=None
            )
        except Exception as e2:
            logger.error(f"Error al enviar mensaje de respaldo: {e2}")
            return None