# =====================================
# test_consola.py
# =====================================
# Este archivo permite simular el chat de MindCare directamente en la consola.
# Analiza los mensajes del usuario para determinar sentimiento y nivel de riesgo,
# y muestra un feedback inmediato en pantalla, con alertas si es necesario.

import sys

# =====================================
# Importación del motor de análisis
# =====================================
# Intentamos importar las funciones de análisis de sentimiento
# Si no están disponibles, se muestra un mensaje de error y se termina el script.
try:
    from analisis_sentimiento import analizar_nota, detectar_nivel_riesgo
except ModuleNotFoundError:
    print("Error: No se encuentra el módulo analisis_sentimiento.py.")
    print("Asegúrate de que 'analisis_sentimiento.py' y 'test_consola.py' estén en la misma carpeta (ia_core).")
    sys.exit(1)

# =====================================
# Función principal del chat en consola
# =====================================
def iniciar_chat_consola():
    """
    Inicia un chat simulado en la consola para evaluar mensajes de un usuario.

    Flujo paso a paso:
    1. Muestra bienvenida y explicaciones de comandos.
       - 'salir' o 'exit' termina la sesión.
    2. Bucle infinito para recibir mensajes del usuario:
       a. Lee el mensaje desde la consola.
       b. Si el mensaje es vacío, lo ignora.
       c. Si el mensaje es 'salir' o 'exit', termina el chat con mensaje de despedida.
       d. Analiza el mensaje usando 'analizar_nota' para detectar sentimiento.
       e. Detecta el nivel de riesgo con 'detectar_nivel_riesgo'.
       f. Prepara un mensaje de alerta según el nivel de riesgo:
          - ALTO: 🚨 Alerta de riesgo alto.
          - MEDIO: ⚠️ Riesgo medio, sugerencia de apoyo.
          - BAJO: ✅ Riesgo bajo.
       g. Imprime en consola los resultados:
          → Clasificación del sentimiento
          → Puntuación numérica
          → Nivel de riesgo
          → Mensaje de alerta correspondiente
    """
    print("\n--- 🧠 MindCare Chat (Modo Consola) ---")
    print("Escribe 'salir' o 'exit' para terminar la sesión.")
    print("-" * 35)

    while True:
        try:
            texto_usuario = input("👤 Tú: ")
        except EOFError:
            break  # En caso de cierre forzado de la consola

        if texto_usuario.lower() in ["salir", "exit"]:
            print("👋 Sesión finalizada. Cuídate.")
            break
        
        if not texto_usuario.strip():  # Ignora mensajes vacíos
            continue

        # 1. Analizar el mensaje (motor de reglas simple)
        analisis = analizar_nota(texto_usuario)
        riesgo = detectar_nivel_riesgo(texto_usuario, analisis)

        # 2. Preparar el feedback para la consola
        clasificacion = analisis['clasificacion']
        puntuacion = analisis['puntuacion_compuesta']
        
        # Estilo de la respuesta según nivel de riesgo
        if riesgo == "ALTO":
            alerta = "🚨 ALERTA DE RIESGO ALTO. BUSCA AYUDA INMEDIATA. 🚨"
        elif riesgo == "MEDIO":
            alerta = "⚠️ Riesgo Medio detectado. Se sugiere buscar apoyo."
        else:
            alerta = "✅ Riesgo Bajo. Estado emocional evaluado."

        # 3. Imprimir resultados
        print("\n🤖 MindCare IA (Análisis):")
        print(f"   → Sentimiento: {clasificacion} (Puntuación: {puntuacion:.3f})")
        print(f"   → Evaluación de Riesgo: {riesgo}")
        print(f"   → Mensaje: {alerta}\n")

# =====================================
# Ejecuta el chat si se llama directamente
# =====================================
if __name__ == "__main__":
    iniciar_chat_consola()
