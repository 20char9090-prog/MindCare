# =====================================
# chat_psicologo.py
# =====================================
# Este script permite interactuar con el usuario directamente
# desde la consola, simulando un chat terapéutico.
# Analiza el texto del usuario para detectar emociones y niveles de riesgo,
# y guarda alertas si es necesario.

import sys
from analisis_sentimiento import analizar_nota, detectar_nivel_riesgo
from db_manager import registrar_usuario_y_obtener_id, registrar_alerta

# =====================================
# Función principal del chat
# =====================================
def iniciar_chat_psicologo():
    """
    Esta función inicia la sesión de chat con el usuario en la consola.
    
    Cómo funciona paso a paso:
    1. Muestra un mensaje de bienvenida y solicita el nombre de usuario.
       - Si no ingresa nada, se usa 'anonimo'.
    2. Registra al usuario en la base de datos y obtiene su ID.
    3. Inicia un bucle de interacción:
       - El usuario escribe un mensaje.
       - Si escribe 'salir' o 'exit', se termina el chat con un mensaje de despedida.
       - Si el mensaje está vacío, se ignora y se pide otro.
       - Analiza el mensaje usando 'analizar_nota' para detectar sentimiento.
       - Detecta el nivel de riesgo con 'detectar_nivel_riesgo'.
       - Si el riesgo es MEDIO o ALTO, se registra una alerta en la base de datos.
       - Muestra en la consola:
         → Clasificación del mensaje (positivo, negativo, extremo, neutro)
         → Puntuación numérica del sentimiento
         → Nivel de riesgo
    """
    print("\n--- 🧠 MindCare (Asistente Terapéutico) ---")
    user_uuid = input("Ingresa tu nombre de usuario para iniciar sesión: ").strip()
    if not user_uuid:
        user_uuid = "anonimo"

    # Registramos al usuario en la base de datos (o lo buscamos si ya existe)
    usuario_id = registrar_usuario_y_obtener_id(user_uuid)
    print(f"Hola {user_uuid}, estoy aquí para escucharte. Escribe 'salir' para terminar.\n")

    while True:
        texto_usuario = input("👤 Tú: ")
        if texto_usuario.lower() in ["salir", "exit"]:
            print("👋 MindCare: Ha sido valiente al compartir. Cuídate y vuelve cuando quieras.")
            break

        if not texto_usuario.strip():  # Ignora mensajes vacíos
            continue

        # Analizamos el sentimiento del mensaje
        analisis = analizar_nota(texto_usuario)
        # Detectamos el nivel de riesgo basado en el análisis
        riesgo = detectar_nivel_riesgo(texto_usuario, analisis)

        # Guardamos alerta en la base de datos si el riesgo es MEDIO o ALTO
        if riesgo in ["MEDIO", "ALTO"]:
            registrar_alerta(usuario_id, texto_usuario, analisis, riesgo)

        # Mostramos al usuario los resultados del análisis
        print(f"\n🤖 MindCare IA:")
        print(f"   → Clasificación: {analisis['clasificacion']}")
        print(f"   → Puntuación: {analisis['puntuacion_compuesta']:.3f}")
        print(f"   → Nivel de Riesgo: {riesgo}\n")

# =====================================
# Ejecutamos la función principal si se corre directamente
# =====================================
if __name__ == "__main__":
    iniciar_chat_psicologo()
