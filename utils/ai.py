"""
AI service using Groq (primary, free) and Gemini (backup, free).
Parses natural language messages into structured coffee business operations.
"""
import json
import logging
import requests

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres un asistente para un negocio de café en Perú.
Tu tarea es entender el mensaje del usuario y extraer datos para registrar una operación.

Acciones posibles:
- compra: Compra de café al proveedor. Datos: tipo_cafe (CEREZO, MOTE o PERGAMINO), proveedor (nombre), cantidad (número en kg), precio (número en S/ por kg)
- gasto: Gasto operativo. Datos: concepto (descripción), monto (número en S/), categoria (Operativo, Mantenimiento, Transporte, Personal, Insumos, Servicios u Otro)
- adelanto: Adelanto de dinero a un proveedor. Datos: proveedor (nombre), monto (número en S/)
- desconocido: No se entiende qué operación quiere el usuario

Responde SIEMPRE con un JSON válido con esta estructura exacta:
{
  "accion": "compra|gasto|adelanto|desconocido",
  "entendido": true,
  "datos": {
    "campo1": valor1,
    "campo2": valor2
  },
  "confirmacion": "Resumen en español de lo entendido",
  "faltante": ["lista", "de", "campos", "que", "faltan"]
}

Reglas importantes:
- tipo_cafe debe ser exactamente CEREZO, MOTE o PERGAMINO (en mayúsculas)
- cantidad, precio y monto deben ser números (float), no strings
- Si el usuario escribe coma como decimal (ej: 2,5), conviértelo a 2.5
- "soles", "lucas", "S/" se refieren a la moneda peruana (PEN)
- Si el usuario dice "cerezo", "cereza" → tipo_cafe: CEREZO
- Si el usuario dice "mote", "maíz" → tipo_cafe: MOTE
- Si el usuario dice "pergamino", "café pergamino" → tipo_cafe: PERGAMINO
- Para gastos, infiere la categoría del concepto si no se especifica
- faltante debe listar solo los campos que NO se pudieron extraer del mensaje

Ejemplos:
- "compré 50 kilos de cerezo a Juan a 3 soles el kilo"
  → accion: compra, datos: {tipo_cafe: CEREZO, proveedor: Juan, cantidad: 50, precio: 3}, faltante: []
- "gasté 200 soles en combustible para el camión"
  → accion: gasto, datos: {concepto: combustible para el camión, monto: 200, categoria: Transporte}, faltante: []
- "le di un adelanto de 500 a María"
  → accion: adelanto, datos: {proveedor: María, monto: 500}, faltante: []
- "compré cerezo a Pedro"
  → accion: compra, datos: {tipo_cafe: CEREZO, proveedor: Pedro}, faltante: [cantidad, precio]
"""


def _call_groq(message: str, groq_api_key: str) -> dict | None:
    """Call Groq API with llama-3.3-70b-versatile."""
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=10,
        )
        if response.status_code == 200:
            content = response.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        logger.error(f"Groq error {response.status_code}: {response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"Groq call failed: {e}")
        return None


def _call_gemini(message: str, gemini_api_key: str) -> dict | None:
    """Call Gemini 1.5 Flash as backup."""
    try:
        prompt = f"{SYSTEM_PROMPT}\n\nMensaje del usuario: {message}\n\nResponde solo con el JSON:"
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1},
            },
            timeout=10,
        )
        if response.status_code == 200:
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            # Strip markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
        logger.error(f"Gemini error {response.status_code}: {response.text[:200]}")
        return None
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        return None


def parse_message(message: str, groq_api_key: str = None, gemini_api_key: str = None) -> dict:
    """
    Parse a natural language message using Groq (primary) or Gemini (backup).

    Returns a dict with keys: accion, entendido, datos, confirmacion, faltante.
    """
    result = None

    if groq_api_key:
        result = _call_groq(message, groq_api_key)

    if result is None and gemini_api_key:
        logger.info("Groq unavailable or no key, trying Gemini...")
        result = _call_gemini(message, gemini_api_key)

    if result is None:
        return {
            "accion": "desconocido",
            "entendido": False,
            "datos": {},
            "confirmacion": "No pude conectarme al asistente de IA. Intenta usar los comandos directos: /compra, /gasto, /adelanto",
            "faltante": [],
        }

    # Ensure faltante is always a list
    if "faltante" not in result:
        result["faltante"] = []

    return result
