import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import db_manager as db  # Este módulo maneja todo lo relacionado con la base de datos

# Inicializamos la app Flask y permitimos solicitudes desde cualquier frontend
app = Flask(__name__)
CORS(app)

# ------------------------------
# Configuración del modelo Ollama
# ------------------------------
OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Endpoint local del modelo Ollama
OLLAMA_MODEL_NAME = "llama3.2:1b"  # Modelo que vamos a usar

# =====================================
# Función para generar respuesta de la IA
# =====================================
def generar_respuesta_con_ia(mensaje_usuario: str, clasificacion: str, username: str) -> str:
    """
    Esta función se encarga de generar la respuesta de la IA de manera empática.
    
    Lo que hace:
    1. Recibe el mensaje que escribió el usuario, la clasificación del mensaje
       y su nombre para personalizar la respuesta.
    2. Construye un prompt que le dice al modelo que actúe como un amigo cercano,
       que responda de manera cálida, humana y breve.
    3. Hace la petición al modelo Ollama con parámetros que permiten respuestas
       creativas y con contexto suficiente.
    4. Limpia la respuesta de caracteres innecesarios.
    5. Si la IA falla o devuelve vacío, retorna un mensaje de apoyo simple.
    """
    prompt = f"""
Eres un amigo cercano y comprensivo. Tu objetivo es acompañar y escuchar. 
Responde de manera cálida, humana y concisa, como hablarías frente a un amigo. 
No repitas ideas ni hagas preguntas múltiples. Sé natural y cercano, 
solo ofrece apoyo y comprensión.

Tu amigo {username} dice: "{mensaje_usuario}"

Responde de manera empática y clara, con frases cortas y cálidas.
"""
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.95,
            "num_predict": 200,
            "top_p": 0.95,
            "num_ctx": 512
        }
    }

    try:
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        respuesta = data.get("response", "").strip()
        respuesta = respuesta.replace("*", "").strip()
        return respuesta if respuesta else f"Aquí estoy contigo, {username}."
    except Exception as e:
        print(f"Error IA: {e}")
        return f"Aquí estoy contigo, {username}."

# =====================================
# Función para analizar el sentimiento
# =====================================
def analizar_nota(texto: str):
    """
    Esta función revisa el mensaje del usuario para clasificar su sentimiento.
    
    Cómo funciona:
    1. Convierte todo el texto a minúsculas para comparar fácilmente.
    2. Busca palabras que indiquen riesgo extremo (como 'suicidio', 'morir').
       Si encuentra alguna, marca el mensaje como EXTREMO.
    3. Busca palabras negativas (tristeza, ansiedad, miedo) y lo marca como NEGATIVO.
    4. Busca palabras positivas (feliz, contento, genial) y lo marca como POSITIVO.
    5. Si no encuentra nada, lo marca como NEUTRO.
    6. Devuelve la clasificación y una puntuación numérica aproximada del sentimiento.
    """
    texto_lower = texto.lower()
    
    palabras_extremas = ["morir", "suicidio", "matarme", "acabar con", "no quiero vivir"]
    if any(palabra in texto_lower for palabra in palabras_extremas):
        return {"clasificacion": "EXTREMO", "puntuacion_compuesta": -1.0}
    
    palabras_negativas = ["mal", "triste", "deprimido", "ansiedad", "miedo", "solo", "desesperado"]
    if any(palabra in texto_lower for palabra in palabras_negativas):
        return {"clasificacion": "NEGATIVO", "puntuacion_compuesta": -0.7}
    
    palabras_positivas = ["bien", "feliz", "alegre", "contento", "mejor", "genial"]
    if any(palabra in texto_lower for palabra in palabras_positivas):
        return {"clasificacion": "POSITIVO", "puntuacion_compuesta": 0.8}
    
    return {"clasificacion": "NEUTRO", "puntuacion_compuesta": 0.1}

# =====================================
# Función para detectar el nivel de riesgo
# =====================================
def detectar_nivel_riesgo(texto: str, analisis: dict) -> str:
    """
    Esta función toma el resultado del análisis de sentimiento
    y decide si el riesgo del usuario es BAJO, MEDIO o ALTO.
    
    Cómo funciona:
    - Si la clasificación es EXTREMO → ALTO
    - Si la puntuación es negativa fuerte → MEDIO
    - Si es neutro o positivo → BAJO
    """
    if analisis["clasificacion"] == "EXTREMO":
        return "ALTO"
    if analisis["puntuacion_compuesta"] < -0.6:
        return "MEDIO"
    return "BAJO"

# =====================================
# Función que maneja el chat
# =====================================
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Esta ruta recibe el mensaje del usuario y devuelve:
    1. La respuesta de la IA.
    2. El análisis de sentimiento y el nivel de riesgo.
    3. Guarda alertas en la base de datos si el riesgo es MEDIO o ALTO.
    
    Qué hace paso a paso:
    - Toma los datos enviados: mensaje, user_id y username.
    - Valida que los campos obligatorios estén presentes.
    - Analiza el sentimiento con 'analizar_nota'.
    - Genera la respuesta empática con 'generar_respuesta_con_ia'.
    - Registra la interacción en la base de datos y guarda alertas si es necesario.
    - Devuelve toda la información al frontend.
    """
    try:
        data = request.json
        mensaje_usuario = data.get("mensaje", "").strip()
        user_id = data.get("user_id")
        username = data.get("username", "Usuario")

        if not mensaje_usuario or not user_id:
            return jsonify({"error": "Campos 'mensaje' y 'user_id' obligatorios."}), 400

        analisis = analizar_nota(mensaje_usuario)
        respuesta_final = generar_respuesta_con_ia(mensaje_usuario, analisis["clasificacion"], username)
        
        try:
            usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
            riesgo = detectar_nivel_riesgo(mensaje_usuario, analisis)
            if riesgo in ["MEDIO", "ALTO"]:
                db.registrar_alerta(usuario_db_id, mensaje_usuario, analisis, riesgo)
        except Exception as db_error:
            print(f"Error en BD: {db_error}")

        return jsonify({
            "respuesta": respuesta_final,
            "analisis": {
                "riesgo": detectar_nivel_riesgo(mensaje_usuario, analisis),
                "clasificacion": analisis["clasificacion"],
                "puntuacion": analisis["puntuacion_compuesta"]
            }
        }), 200
    except Exception as e:
        print(f"Error en /api/chat: {e}")
        return jsonify({
            "error": "Error interno del servidor",
            "respuesta": "Lo siento, hubo un problema. ¿Puedes intentar nuevamente?"
        }), 500

# =====================================
# Función que devuelve todas las alertas de un usuario
# =====================================
@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """
    Esta ruta recibe un user_id y devuelve todas las alertas registradas para ese usuario.
    
    Paso a paso:
    - Recibe user_id por query string.
    - Valida que llegue.
    - Busca el usuario en la base de datos.
    - Devuelve todas sus alertas en formato JSON.
    """
    try:
        user_uuid = request.args.get("user_id")
        if not user_uuid:
            return jsonify({"error": "Falta user_id"}), 400

        usuario_db_id = db.registrar_usuario_y_obtener_id(user_uuid)
        alerts = db.obtener_alertas(usuario_db_id)
        return jsonify({"alerts": alerts}), 200
    except Exception as e:
        print(f"Error en /api/alerts: {e}")
        return jsonify({"error": "Error al obtener alertas"}), 500

# =====================================
# Función que devuelve estadísticas de usuario
# =====================================
@app.route("/api/stats", methods=["GET"])
def stats():
    """
    Esta ruta devuelve estadísticas de un usuario:
    - Total de interacciones
    - Último estado detectado
    - Conteo de alertas por nivel de riesgo
    
    Cómo funciona:
    - Recibe user_id por query string y valida que llegue.
    - Busca todas las alertas del usuario.
    - Cuenta cuántas son BAJO, MEDIO y ALTO.
    - Devuelve todo en formato JSON.
    """
    try:
        user_uuid = request.args.get("user_id")
        if not user_uuid:
            return jsonify({"error": "Falta user_id"}), 400

        usuario_db_id = db.registrar_usuario_y_obtener_id(user_uuid)
        alerts = db.obtener_alertas(usuario_db_id)

        conteo_riesgo = {"BAJO": 0, "MEDIO": 0, "ALTO": 0}
        for alert in alerts:
            conteo_riesgo[alert["riesgo"]] += 1

        total_interacciones = len(alerts)
        ultimo_estado = alerts[0]["clasificacion"] if alerts else "NEUTRO"

        return jsonify({
            "total_interacciones": total_interacciones,
            "ultimo_estado": ultimo_estado,
            "conteo_riesgo": conteo_riesgo
        }), 200
    except Exception as e:
        print(f"Error en /api/stats: {e}")
        return jsonify({"error": "Error al obtener estadísticas"}), 500

# =====================================
# Ejecutamos la app
# =====================================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
