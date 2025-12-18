# MindCare — Deep Dive en IA

Este documento describe en detalle la implementación, el diseño y las decisiones técnicas relacionadas con la parte de IA del proyecto MindCare. Está pensado para la diapositiva "IA en profundidad" y para que puedas explicar con precisión cómo funciona la generación de respuestas y el manejo de riesgo.

---

## Resumen rápido
- Motor: llamadas HTTP a un servidor local de Ollama (`CONFIG['OLLAMA_API_URL']`).
- Prompt: prompt controlado y seguro en `crear_prompt()` (ver más abajo).
- Parámteros del modelo: `temperature`, `num_predict`, `top_p`, `num_ctx` ajustados según nivel de riesgo.
- Fallback: `generar_respuesta_fallback()` con mensajes seguros por nivel de riesgo.
- Seguridad: no revelar que es IA, no dar diagnósticos médicos, manejo especial para ideación suicida.

---

## Archivos relevantes
- `ia_core/api_chat.py` — orquesta el flujo de mensajes; contiene `crear_prompt()`, `generar_respuesta_con_ia()` y el endpoint `/api/chat`.
- `ia_core/analisis_sentimiento.py` — motor de análisis que devuelve clasificación y nivel de riesgo (modularizable).
- `ia_core/db_manager.py` — persiste mensajes y alertas en `mensajes` y `alertas`.

---

## Flujo de un mensaje (resumido)
1. El frontend envía `POST /api/chat` con `mensaje`, `user_id` y `username`.
2. Backend: `procesar_analisis(mensaje)` usa `analisis_sentimiento.analisis_completo()` para clasificar.
3. Backend: `generar_respuesta_con_ia()` crea el prompt (func `crear_prompt`) e invoca Ollama.
4. Si la llamada a Ollama falla o devuelve vacío, `generar_respuesta_fallback()` se usa.
5. Se guardan los mensajes en la DB (`guardar_mensaje`) y se registran alertas según riesgo.
6. Si riesgo ALTO -> posible notificación (solo nombre + nivel — sin texto completo).

---

## Prompt (controlado)
El prompt está en `crear_prompt(mensaje, riesgo, username)`. Puntos clave:
- Obliga a respuestas en español.
- Respuestas breves: 2–3 frases, <40 palabras idealmente.
- Incluye reglas claras: no revelar que es IA, no dar consejos médicos, validar emociones, preguntar suavemente.
- Manejo de riesgo: instrucciones específicas si el usuario expresa autolesión o ideación suicida (validación + indicación de buscar ayuda inmediata).
- Usa el `username` para personalizar sin exponer identificadores internos.

**Ejemplo condensado extraído del prompt:**
> "Eres un amigo muy cercano y de confianza para {username}. Responde siempre breve, cálida y directa. Valida emociones. Si hay ideación suicida: valida y sugiere buscar ayuda inmediata (servicios de emergencia), ofrécete como compañía. No des diagnósticos ni digas que eres IA. Usa el nombre {username}."

---

## Payload a Ollama (implementación)
En `generar_respuesta_con_ia()` se construye:

```json
{
  "model": CONFIG["OLLAMA_MODEL_NAME"],
  "prompt": "...",
  "stream": false,
  "options": {
    "temperature": 0.85 (si riesgo == "ALTO") o 0.95 (si no),
    "num_predict": 150 (ALTO) o 200 (otro),
    "top_p": 0.9 (ALTO) o 0.95 (otro),
    "num_ctx": 512
  }
}
```

- `temperature` menor en riesgo ALTO para respuestas más conservadoras.
- `num_predict` recortado en ALTO para respuestas compactas.

---

## Fallbacks y robustez
- Si `requests.post` falla o la respuesta está vacía, se usa `generar_respuesta_fallback(riesgo, username)` que devuelve una frase segura por nivel.
- La lógica asegura siempre devolver algo y evita bloquear la experiencia del usuario.

---

## Seguridad y privacidad en la capa IA
- El prompt prohíbe a la IA mencionar que es una IA.
- Las notificaciones externas (Pushbullet, IFTTT) no envían texto completo; solo indican `Alerta: riesgo ALTO en {username}`.
- Evitar exponer tokens en logs o variables de entorno comprometidas.

---

## Ejemplos de intercambio (para demo)
- Usuario: "Me siento muy solo desde que me mudé"
- Prompt incluye: `"{username}: \"Me siento muy solo desde que me mudé\""`
- Respuesta esperada (IA): "Siento que te sientes solo por el cambio, {username}. Estoy aquí contigo — ¿quieres contarme qué fue lo más difícil?"

---

## Metricas y telemetría (recomendado)
- Registrar latencia de llamadas a Ollama.
- Contabilizar tasa de fallback por minuto (si aumenta -> revisar modelo/servicio local).
- Monitorear frecuencia de riesgo ALTO y acciones posteriores (notificaciones enviadas).

---

## Recomendaciones para mejorar la IA (roadmap técnico)
1. Experimentos con `temperature` y `top_p` por perfil de usuario (A/B tests).
2. Incorporar contexto de conversación (historial corto) en el prompt para respuestas más coherentes.
3. Considerar `safety classifier` adicional para detectar lenguaje autolesivo antes de enviarlo a IA.
4. Evaluación humana: revisar muestras aleatorias de respuestas para calibrar el prompt.
5. Documentar y versionar prompts (prompt engineering) para reproducibilidad.

---

## Cómo probar localmente (comandos)
```powershell
# Iniciar servidor
python .\api_chat.py

# Enviar mensaje de prueba
Invoke-RestMethod -Method Post -ContentType 'application/json' -Body '{"mensaje":"me siento mal","user_id":"demo","username":"demo"}' 'http://127.0.0.1:5000/api/chat' | ConvertTo-Json

# Ver historial
Invoke-RestMethod 'http://127.0.0.1:5000/api/messages?user_id=demo' | ConvertTo-Json
```

---

## Archivo(s) donde mirar para la presentación
- `ia_core/api_chat.py`: prompt y llamada a Ollama
- `ia_core/analisis_sentimiento.py`: motor de clasificación
- `ia_core/db_manager.py`: almacenamiento y registro de alertas

---

Si quieres, puedo crear una diapositiva PPTX basada en este documento (con notas del orador). ¿Lo deseas? También puedo convertir este `AI_DEEP_DIVE.md` en una diapositiva Reveal.js automáticamente.
