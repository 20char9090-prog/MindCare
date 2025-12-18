---
title: MindCare — IA (Deep Dive)
---

# Slide 1 — Título

MindCare — IA en profundidad

- Presentador: [Tu nombre]
- Fecha

---

# Slide 2 — Objetivo de la IA

- Proveer respuestas empáticas y seguras.
- Detectar niveles de riesgo emocional.
- Preservar privacidad y notificar solo cuando es necesario.

Speaker notes: Enfatizar uso local opcional de Ollama para privacidad.

---

# Slide 3 — Componentes IA

- `crear_prompt()` — control de comportamiento
- `generar_respuesta_con_ia()` — llamada a Ollama
- `generar_respuesta_fallback()` — respaldo

Speaker notes: Mostrar líneas clave del prompt y cómo se compone el payload.

---

# Slide 4 — Prompt (ejemplo)

Mostrar el prompt mejorado (resumido):

> "Eres un amigo muy cercano y de confianza para {username}. Responde siempre breve, cálida y directa... Si hay ideación suicida: valida y sugiere buscar ayuda inmediata. No des diagnósticos ni digas que eres IA."

Speaker notes: Explicar por qué las restricciones son importantes (ética y seguridad).

---

# Slide 5 — Payload a Ollama

- `temperature`: 0.85 (ALTO) / 0.95 (otro)
- `num_predict`: 150/200
- `top_p`: 0.9/0.95
- `num_ctx`: 512

Speaker notes: Comentar cómo afectan estos parámetros al tono y creatividad.

---

# Slide 6 — Fallback y seguridad

- Fallback textual por nivel de riesgo.
- Notificaciones: sólo nombre y nivel (no texto).
- Backup antes de migraciones.

Speaker notes: Mostrar ejemplo de fallback para ALTO.

---

# Slide 7 — Métricas IA

- Latencia de respuesta
- % de fallbacks
- Tasa de respuestas clasificadas como ALTO

Speaker notes: Proponer monitorización con simples métricas y alarmas.

---

# Slide 8 — Roadmap IA

- A/B tests de prompts
- Contexto de conversación (memoria de corto plazo)
- Clasificador de seguridad previo a la IA
- Integración con recursos locales en riesgo ALTO

---

# Slide 9 — Demo (pasos)

1. Abrir terminal: `python .\api_chat.py`
2. Enviar POST a `/api/chat`
3. Mostrar respuesta y entrada guardada en `/api/messages`

---

# Slide 10 — Preguntas

Abrir para Q&A.

Speaker notes: Tener preparados 2–3 ejemplos de prompts y estadísticas extra.
