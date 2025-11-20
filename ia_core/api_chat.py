import json
import logging
from typing import Dict
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import db_manager as db
from analisis_sentimiento import analisis_completo

# =======================
# Configuración
# =======================
CONFIG = {
    "OLLAMA_API_URL": "http://localhost:11434/api/generate",
    "OLLAMA_MODEL_NAME": "qwen2.5:1.5b",
    "OLLAMA_TIMEOUT": 60
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)
CORS(app)

# =======================
# Funciones auxiliares
# =======================
def generar_respuesta_con_ia(mensaje: str, clasificacion: str, riesgo: str, username: str) -> str:
    """Genera respuesta empática con IA Ollama según riesgo."""
    prompt = crear_prompt(mensaje, riesgo, username)
    payload = {
        "model": CONFIG["OLLAMA_MODEL_NAME"],
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.85 if riesgo == "ALTO" else 0.95,
            "num_predict": 150 if riesgo == "ALTO" else 200,
            "top_p": 0.9 if riesgo == "ALTO" else 0.95,
            "num_ctx": 512
        }
    }
    try:
        response = requests.post(CONFIG["OLLAMA_API_URL"], json=payload, timeout=CONFIG["OLLAMA_TIMEOUT"])
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").replace("*", "").strip() or generar_respuesta_fallback(riesgo, username)
    except requests.RequestException as e:
        logging.error(f"Error IA Ollama: {e}")
        return generar_respuesta_fallback(riesgo, username)

def crear_prompt(mensaje: str, riesgo: str, username: str) -> str:
    """
    Prompt para respuesta breve, cálida y cercana, como un amigo de confianza.
    """
    return f"""
    Eres como un amigo muy cercano para {username}. Responde siempre de forma breve, cálida, humana y directa, mencionando de manera emocional lo que {username} escribió. No des diagnósticos ni consejos médicos. No menciones que eres una IA. Si el usuario expresa algo difícil, valida sus emociones y hazle sentir acompañado, como lo haría un buen amigo.

    Mensaje del usuario:
    {username}: "{mensaje}"

    Responde con una frase corta, cálida y empática, mencionando lo que {username} contó. Ejemplo: "Siento mucho que hayas perdido una materia, {username}. Aquí estoy para ti, cuenta conmigo." Sé siempre cercano y humano.
    """

def generar_respuesta_fallback(riesgo: str, username: str) -> str:
    """Respuesta de emergencia si IA falla."""
    respuestas = {
        "ALTO": f"{username}, lo que sientes es importante. Considera hablar con un profesional.",
        "MEDIO": f"Estoy aquí para escucharte, {username}.",
        "BAJO": f"Aquí estoy contigo, {username}."
    }
    return respuestas.get(riesgo, f"Aquí estoy contigo, {username}.")

def procesar_analisis(mensaje: str) -> Dict:
    """Ejecuta análisis de sentimientos y riesgo usando motor sofisticado."""
    resultado = analisis_completo(mensaje)
    return {
        "clasificacion": resultado["sentimiento"]["clasificacion"],
        "puntuacion_compuesta": resultado["sentimiento"]["puntuacion"],
        "puntuacion": resultado["sentimiento"]["puntuacion"],
        "riesgo": resultado["riesgo"]["nivel"],
        "valor": resultado["riesgo"].get("valor"),
        "motivos": resultado["riesgo"]["motivos"],
        "contenido_extremo": resultado["sentimiento"]["contenido_extremo"]
    }

def registrar_alerta_si_corresponde(user_id: str, mensaje: str, analisis: Dict):
    """Registra una alerta en la DB para cualquier nivel de riesgo.

    Antes sólo se registraban las alertas `MEDIO` y `ALTO`. Ahora se almacenan
    también las de `BAJO` para que aparezcan en la ventana de alertas e historial.
    Se mantiene un logging con distinto nivel según la gravedad.
    """
    usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
    # Pasar el valor numérico del riesgo al registrar la alerta
    valor = analisis.get("valor")
    db.registrar_alerta(usuario_db_id, mensaje, analisis, analisis["riesgo"], valor)

    # Logging por severidad
    if analisis["riesgo"] == "ALTO":
        logging.warning(f"ALERTA ALTO registrada para {user_id}: {analisis.get('motivos', [])[:2]}")
    elif analisis["riesgo"] == "MEDIO":
        logging.warning(f"Alerta MEDIO registrada para {user_id}: {analisis.get('motivos', [])[:2]}")
    else:
        logging.info(f"Alerta BAJO registrada para {user_id}.")



# =======================
# Endpoints Flask
# =======================
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    mensaje = data.get("mensaje", "").strip()
    user_id = data.get("user_id")
    username = data.get("username", "Usuario")

    if not mensaje or not user_id:
        return jsonify({"error": "Campos 'mensaje' y 'user_id' son obligatorios."}), 400

    analisis = procesar_analisis(mensaje)
    respuesta = generar_respuesta_con_ia(mensaje, analisis["clasificacion"], analisis["riesgo"], username)
    try:
        registrar_alerta_si_corresponde(user_id, mensaje, analisis)
    except Exception as e:
        logging.error(f"Error en registro de alerta: {e}")

    return jsonify({"respuesta": respuesta, "analisis": analisis}), 200

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Falta el parámetro 'user_id'"}), 400
    usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
    if usuario_db_id == -1:
        return jsonify({"error": "Usuario no encontrado"}), 404
    alertas = db.obtener_alertas(usuario_db_id)
    return jsonify({"user_id": user_id, "alerts": alertas}), 200

# NUEVO ENDPOINT: /api/stats
@app.route("/api/stats", methods=["GET"])
def get_stats():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Falta el parámetro 'user_id'"}), 400
    usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
    if usuario_db_id == -1:
        return jsonify({"error": "Usuario no encontrado"}), 404
    stats = db.obtener_stats_y_tendencia(usuario_db_id)
    return jsonify(stats), 200

@app.route("/api/health", methods=["GET"])
def health():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_status = "OK" if r.status_code == 200 else "ERROR"
    except:
        ollama_status = "OFFLINE"
    return jsonify({"status": "OK", "ollama": ollama_status, "version": "2.0"}), 200

# =======================
# Main
# =======================
if __name__ == "__main__":
    logging.info("🚀 SERVIDOR DE ANÁLISIS EMOCIONAL INICIADO")
    app.run(debug=True, port=5000)
