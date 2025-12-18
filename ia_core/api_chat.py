import json
import logging
from typing import Dict
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import db_manager as db
from analisis_sentimiento import analisis_completo
from notifications import send_notification
from datetime import datetime, timedelta
import os

# =======================
# Configuración
# =======================
CONFIG = {
    "OLLAMA_API_URL": "http://localhost:11434/api/generate",
    "OLLAMA_MODEL_NAME": "qwen2.5:1.5b",
    "OLLAMA_TIMEOUT": 60
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Servir la carpeta `interfaz` como contenido estático en la raíz
app = Flask(__name__, static_folder='interfaz', static_url_path='')
CORS(app)

def _serve_frontend(path: str = ''):
    """Serve frontend files from the interfaz directory."""
    if path == '' or path == '/':
        return send_from_directory('interfaz', 'index.html')
    # Fallback to sending the requested static file
    return send_from_directory('interfaz', path)


# Rutas para servir la interfaz (root y cualquier archivo estático)
@app.route('/', methods=['GET'])
def serve_root():
    return _serve_frontend('index.html')

@app.route('/<path:path>', methods=['GET'])
def serve_static(path):
    return _serve_frontend(path)

# =======================
# Funciones auxiliares
# =======================

# ---------------------------------------------------------------
# FUNCIÓN: generar_respuesta_con_ia
# ---------------------------------------------------------------
# ¿Qué hace?
# Se encarga de comunicarse con la IA local (Ollama) para generar
# una respuesta empática basada en:
#  - El mensaje original del usuario
#  - La clasificación emocional
#  - El nivel de riesgo detectado
#  - El nombre del usuario
#
# Proceso interno:
# 1. Construye un prompt personalizado usando crear_prompt().
# 2. Ajusta parámetros del modelo según el nivel de riesgo.
# 3. Envía la petición HTTP al servidor Ollama.
# 4. Si la IA responde correctamente, limpia y devuelve el texto.
# 5. Si falla, usa una respuesta de respaldo (fallback).
#
# Su objetivo es transformar el análisis emocional en una
# respuesta humana, cercana y empática para el usuario.

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


# ---------------------------------------------------------------
# FUNCIÓN: crear_prompt
# ---------------------------------------------------------------
# ¿Qué hace?
# Construye el texto base (prompt) que se envía al modelo de IA.
#
# Este prompt define el comportamiento que debe tener la IA:
#  - Hablar como un amigo cercano
#  - Ser cálido y empático
#  - No mencionar que es una IA
#  - No dar diagnósticos médicos
#
# Incluye el mensaje original del usuario y su nombre
# para que la respuesta sea más personalizada y humana.

def crear_prompt(mensaje: str, riesgo: str, username: str) -> str:
    """
    Prompt para respuesta breve, cálida y cercana, como un amigo de confianza.
    """
    return f"""
    Eres un amigo muy cercano y de confianza para {username}. Habla siempre en español.

        Tonalidad y estilo:
        - Breve: máximo 2-3 frases (preferiblemente menos de 40 palabras).
        - Cálido, humano y directo: usa lenguaje sencillo, afectuoso y sin tecnicismos.
        - No juzgues ni minimices lo que la persona siente.
        - No digas que eres una IA, ni que eres un profesional de la salud.

        Contenido y comportamiento:
        - Refleja la emoción principal del mensaje (parafrasea brevemente), por ejemplo: "Parece que te sientes abrumado/ triste/ angustiado".
        - Valida: ofrece una frase de validación emocional: "Tiene sentido que te sientas así" o similar.
        - Acompaña: transmite compañía y disponibilidad: "Estoy aquí contigo".
        - Ofrece una acción pequeña y segura (solo una): por ejemplo, sugerir respirar profundamente tres veces, dar un paso pequeño o buscar a alguien de confianza.
        - Haz una pregunta abierta y suave para invitar a seguir hablando, una sola (por ejemplo: "¿Quieres contarme más sobre eso?").

        Límites y seguridad:
        - Nunca des diagnósticos ni consejos médicos ni instrucciones clínicas.
        - Si el usuario expresa ideas de autolesión, suicidio o peligro inminente, responde con:
            una validación empática breve + una indicación clara de buscar ayuda inmediata
            y sugiere contactar a una persona de confianza o un profesional. No minimices el riesgo.
        - No repitas información sensible más de lo necesario; al parafrasear, evita divulgar detalles íntimos innecesarios.

        Responde siempre usando el nombre del usuario ("{username}") al menos una vez, de forma natural.

        Ejemplos de respuesta (formato esperado):
        - Usuario: "Me siento muy solo desde que cambié de ciudad"
            Respuesta: "Siento que te sientes solo por el cambio, {username}. Estoy aquí contigo — ¿quieres contarme qué fue lo más difícil?"

        - Usuario (alto riesgo): "No quiero vivir más"
            Respuesta: "Lo siento mucho, {username}, suena que estás pasando por un momento muy doloroso. Por favor, busca ayuda ahora: contacta servicios de emergencia o una línea de ayuda. Si quieres, puedo quedarme aquí mientras me cuentas más."

        Mensaje del usuario:
        {username}: "{mensaje}"

        Responde ahora siguiendo estrictamente estas instrucciones.
        """


# ---------------------------------------------------------------
# FUNCIÓN: generar_respuesta_fallback
# ---------------------------------------------------------------
# ¿Qué hace?
# Devuelve una respuesta básica y segura cuando la IA falla
# o no responde correctamente.
#
# Garantiza que el usuario siempre reciba una respuesta,
# incluso si el servicio de IA está caído.
#
# Las respuestas varían según el nivel de riesgo.

def generar_respuesta_fallback(riesgo: str, username: str) -> str:
    """Respuesta de emergencia si IA falla."""
    respuestas = {
        "ALTO": f"{username}, lo que sientes es importante. Considera hablar con un profesional.",
        "MEDIO": f"Estoy aquí para escucharte, {username}.",
        "BAJO": f"Aquí estoy contigo, {username}."
    }
    return respuestas.get(riesgo, f"Aquí estoy contigo, {username}.")


# ---------------------------------------------------------------
# FUNCIÓN: procesar_analisis
# ---------------------------------------------------------------
# ¿Qué hace?
# Ejecuta el análisis emocional completo del mensaje del usuario
# utilizando el módulo externo analisis_sentimiento.
#
# Extrae y organiza la información más relevante como:
#  - Clasificación emocional
#  - Puntuación
#  - Nivel de riesgo
#  - Motivos del riesgo
#  - Contenido extremo
#
# Devuelve un diccionario estructurado que será usado
# por otras funciones del sistema.

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


# ---------------------------------------------------------------
# FUNCIÓN: registrar_alerta_si_corresponde
# ---------------------------------------------------------------
# ¿Qué hace?
# Registra en la base de datos una alerta por cada mensaje
# procesado, sin importar el nivel de riesgo.
#
# También agrega registros al log con diferente nivel
# según la gravedad del riesgo detectado.
#
# Permite mantener un historial completo para monitoreo
# y análisis posterior del estado emocional del usuario.

def registrar_alerta_si_corresponde(user_id: str, mensaje: str, analisis: Dict, username: str = None):
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
        try:
            usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
            # Use the provided username when available; fall back to user_id.
            nombre = username if username else user_id
            # For privacy and clarity, only include the user's name and risk level in the push.
            text = f"Alerta: se detectó riesgo ALTO en el usuario {nombre}."
            sent = send_notification(None, text)
            if sent:
                # registrar timestamp genérico de envío para este usuario
                try:
                    db.actualizar_ultima_notificacion(usuario_db_id)
                except Exception:
                    logging.debug("No se pudo actualizar marca de última notificación en DB")
                logging.info(f"Notificación enviada (backend configurado) para usuario {user_id}")
            else:
                logging.error(f"Fallo al enviar notificación para usuario {user_id}")
        except Exception as e:
            logging.error(f"Error al procesar notificación: {e}")
    elif analisis["riesgo"] == "MEDIO":
        logging.warning(f"Alerta MEDIO registrada para {user_id}: {analisis.get('motivos', [])[:2]}")
    else:
        logging.info(f"Alerta BAJO registrada para {user_id}.")


# =======================
# Endpoints Flask
# =======================

# ---------------------------------------------------------------
# ENDPOINT: /api/chat
# ---------------------------------------------------------------
# Recibe un mensaje del frontend y controla todo el flujo:
# 1. Valida datos recibidos
# 2. Procesa análisis emocional
# 3. Genera respuesta con IA
# 4. Registra alerta si aplica
# 5. Devuelve la respuesta al frontend

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    mensaje = data.get("mensaje", "").strip()
    user_id = data.get("user_id")
    username = data.get("username", "Usuario")

    if not mensaje or not user_id:
        return jsonify({"error": "Campos 'mensaje' y 'user_id' son obligatorios."}), 400
    # Asegurar que el usuario esté registrado y su display name actualizado
    try:
        db.registrar_o_actualizar_usuario(user_id, username)
    except Exception as e:
        logging.debug(f"No se pudo actualizar display_name en DB: {e}")

    analisis = procesar_analisis(mensaje)
    respuesta = generar_respuesta_con_ia(mensaje, analisis["clasificacion"], analisis["riesgo"], username)
    try:
        # Registrar alerta y además guardar la conversación (usuario + asistente)
        registrar_alerta_si_corresponde(user_id, mensaje, analisis, username)
        try:
            usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
            # Guardar mensaje del usuario
            db.guardar_mensaje(usuario_db_id, 'user', mensaje, analisis)
            # Guardar respuesta del asistente
            db.guardar_mensaje(usuario_db_id, 'assistant', respuesta, {'respuesta_generada': True})
        except Exception as ee:
            logging.debug(f"No se pudo guardar mensaje en historial: {ee}")
    except Exception as e:
        logging.error(f"Error en registro de alerta: {e}")

    return jsonify({"respuesta": respuesta, "analisis": analisis}), 200


# ---------------------------------------------------------------
# ENDPOINT: /api/alerts
# ---------------------------------------------------------------
# Devuelve todas las alertas registradas para un usuario específico

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


# ---------------------------------------------------------------
# ENDPOINT: /api/user
# ---------------------------------------------------------------
# Registra o actualiza un usuario (display name) en la DB

@app.route("/api/user", methods=["POST"])
def register_user():
    data = request.json or {}
    user_id = data.get("user_id")
    username = data.get("username") or data.get("display_name")
    if not user_id:
        return jsonify({"error": "Falta el parámetro 'user_id'"}), 400
    try:
        usuario_db_id = db.registrar_o_actualizar_usuario(user_id, username)
        if usuario_db_id == -1:
            return jsonify({"error": "Error al acceder a la base de datos"}), 500
        return jsonify({"ok": True, "user_id": user_id, "db_id": usuario_db_id}), 200
    except Exception as e:
        logging.error(f"Error en /api/user: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------
# ENDPOINT: /api/register (con contraseña)
# ---------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or {}
    user_id = data.get("user_id")
    username = data.get("username") or data.get("display_name")
    password = data.get("password")
    if not user_id or not password:
        return jsonify({"error": "Faltan 'user_id' o 'password'"}), 400
    try:
        # crear/actualizar usuario
        db.registrar_o_actualizar_usuario(user_id, username)
        ok = db.set_user_password(user_id, password)
        if not ok:
            return jsonify({"error": "No se pudo guardar la contraseña"}), 500
        usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
        token = db.create_session(usuario_db_id)
        return jsonify({"ok": True, "token": token}), 200
    except Exception as e:
        logging.error(f"Error en /api/register: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------
# ENDPOINT: /api/login
# ---------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json or {}
    user_id = data.get("user_id")
    password = data.get("password")
    if not user_id or not password:
        return jsonify({"error": "Faltan 'user_id' o 'password'"}), 400
    try:
        uid = db.verify_user_password(user_id, password)
        if uid == -1:
            return jsonify({"ok": False, "error": "Credenciales inválidas"}), 401
        token = db.create_session(uid)
        return jsonify({"ok": True, "token": token}), 200
    except Exception as e:
        logging.error(f"Error en /api/login: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------
# ENDPOINT: /api/logout
# ---------------------------------------------------------------
@app.route("/api/logout", methods=["POST"])
def api_logout():
    data = request.json or {}
    token = data.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        return jsonify({"error": "Falta token"}), 400
    try:
        ok = db.delete_session(token)
        return jsonify({"ok": ok}), 200
    except Exception as e:
        logging.error(f"Error en /api/logout: {e}")
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------
# ENDPOINT: /api/stats
# ---------------------------------------------------------------
# Devuelve estadísticas y tendencias emocionales del usuario

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


# ---------------------------------------------------------------
# ENDPOINT: /api/health
# ---------------------------------------------------------------
# Verifica el estado del servidor y la conexión con Ollama

@app.route("/api/health", methods=["GET"])
def health():
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_status = "OK" if r.status_code == 200 else "ERROR"
    except:
        ollama_status = "OFFLINE"
    return jsonify({"status": "OK", "ollama": ollama_status, "version": "2.0"}), 200


# ---------------------------------------------------------------
# ENDPOINT: /api/messages
# ---------------------------------------------------------------
@app.route("/api/messages", methods=["GET"])
def get_messages():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Falta el parámetro 'user_id'"}), 400
    # Buscar todos los usuarios que coincidan por user_id exacto o por display_name
    msgs = []
    try:
        ids = []
        # Exact match user_id
        exact = db.obtener_usuario_id_por_userid_exacto(user_id)
        if exact != -1:
            ids.append(exact)
        # Usuarios con el mismo display_name
        display_ids = db.obtener_usuario_ids_por_display_name(user_id)
        for did in display_ids:
            if did not in ids:
                ids.append(did)

        if not ids:
            # Si no hay coincidencias, crear/registrar el user_id (comportamiento previo)
            usuario_db_id = db.registrar_usuario_y_obtener_id(user_id)
            if usuario_db_id == -1:
                return jsonify({"error": "Usuario no encontrado"}), 404
            ids = [usuario_db_id]

        # Obtener mensajes combinados de todos los ids encontrados
        msgs = db.obtener_mensajes_por_usuario_ids(ids, limit=500)
        return jsonify({"user_id": user_id, "messages": msgs, "source_user_ids": ids}), 200
    except Exception as e:
        logging.error(f"Error en /api/messages: {e}")
        return jsonify({"error": "Error interno"}), 500


# ---------------------------------------------------------------
# ENDPOINT: /api/test_notify
# ---------------------------------------------------------------
# Envía una notificación de prueba usando el backend configurado
@app.route("/api/test_notify", methods=["POST"])
def test_notify():
    data = request.json or {}
    title = data.get('title', 'Prueba MindCare')
    body = data.get('body', 'Esta es una notificación de prueba desde MindCare.')
    try:
        sent = send_notification(None, f"{title}: {body}")
        if sent:
            return jsonify({"ok": True, "message": "Notificación enviada (según backend)."}), 200
        else:
            return jsonify({"ok": False, "message": "El backend devolvió fallo al enviar."}), 500
    except Exception as e:
        logging.error(f"Error en /api/test_notify: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------------------------------------------------------
# ENDPOINT: /api/env_status
# ---------------------------------------------------------------
# Devuelve información no sensible sobre las variables de entorno
# relacionadas con las notificaciones para depuración local.
@app.route("/api/env_status", methods=["GET"])
def env_status():
    backend = os.environ.get("NOTIFICATION_BACKEND", "")
    push_token = os.environ.get("PUSHBULLET_TOKEN")
    has_push = bool(push_token)
    tok_len = len(push_token) if push_token else 0
    return jsonify({
        "notification_backend": backend,
        "has_pushbullet_token": has_push,
        "pushbullet_token_length": tok_len
    }), 200



# ---------------------------------------------------------------
# ENDPOINT: /api/claim
# ---------------------------------------------------------------
@app.route("/api/claim", methods=["POST"])
def api_claim():
    """Reclama/migra mensajes de usuarios temporales hacia un `target_user_id`.

    Payload esperado JSON:
    {
      "target_user_id": "camila",
      "source_user_ids": ["uuid-1", "uuid-2"],
      "dry_run": true  # por defecto true
    }

    Si `dry_run` es true, devuelve un preview de cuántos mensajes serían movidos y los ids involucrados.
    Si `dry_run` es false, hace una copia de seguridad de la DB y realiza la migración.
    """
    data = request.json or {}
    target = data.get('target_user_id')
    sources = data.get('source_user_ids') or []
    dry = data.get('dry_run', True)

    if not target or not sources:
        return jsonify({"error": "Faltan 'target_user_id' o 'source_user_ids'"}), 400

    try:
        # Resolver target a db id (crear si no existe)
        target_db_id = db.registrar_usuario_y_obtener_id(target)
        if target_db_id == -1:
            return jsonify({"error": "No se pudo acceder al usuario target"}), 500

        # Resolver sources a ids existentes (no crear nuevos)
        resolved = []
        for s in sources:
            sid = db.obtener_usuario_id_por_userid_exacto(s)
            if sid != -1:
                resolved.append(sid)

        if not resolved:
            return jsonify({"error": "No se encontraron usuarios fuente existentes"}), 404

        # Contar cuántos mensajes hay en total para preview
        all_msgs = db.obtener_mensajes_por_usuario_ids(resolved, limit=1000000)
        count = len(all_msgs)

        result = {"target_db_id": target_db_id, "source_db_ids": resolved, "messages_to_move": count, "dry_run": bool(dry)}

        if dry:
            return jsonify(result), 200

        # Realizar backup y luego migración
        backup_path = db.backup_db()
        moved = 0
        if backup_path:
            moved = db.transferir_mensajes(resolved, target_db_id)
        else:
            # intentar migrar aun si backup falla
            moved = db.transferir_mensajes(resolved, target_db_id)

        result.update({"backup": backup_path, "moved": moved})
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error en /api/claim: {e}")
        return jsonify({"error": str(e)}), 500




# =======================
# Main
# =======================
if __name__ == "__main__":
    logging.info("🚀 SERVIDOR DE ANÁLISIS EMOCIONAL INICIADO")
    app.run(debug=True, port=5000)