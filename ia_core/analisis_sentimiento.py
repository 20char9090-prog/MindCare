import re, unicodedata, nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# =========================================================
# CONFIGURACIÓN INICIAL Y LÉXICOS
# =========================================================
# En esta primera parte se prepara todo lo necesario para que el sistema
# pueda analizar el sentimiento del mensaje que escriba el usuario.

# Intentamos inicializar VADER, que es una herramienta de análisis de
# sentimientos pensada originalmente para inglés. Aunque no es perfecta
# para español, aporta una puntuación muy útil como base.
try:
    sia = SentimentIntensityAnalyzer()
except LookupError:
    print("Descarga nltk.download('vader_lexicon')")
    sia = None

# Este es un pequeño léxico manual en español. Se usa como complemento
# del análisis de VADER. Básicamente, si detecta palabras positivas suma
# puntos, y si detecta palabras negativas los resta.
LEXICO = {
    "pos": ["feliz", "alegre", "contento", "tranquilo", "bien", "optimista", "esperanza", "motivado"],
    "neg": ["triste", "mal", "fatal", "horrible", "enojado", "rabia", "derrotado", "estresado", "ansioso"]
}

# =========================================================
# FUNCIONES AUXILIARES DE PREPROCESAMIENTO
# =========================================================
# Aquí están funciones pequeñas que "limpian" y preparan el texto.

def norm(t: str) -> str:
    """
    Normaliza el texto para que los análisis funcionen mejor.

    Lo que hace:
    - Pasa todo el texto a minúsculas.
    - Quita tildes para que coincidan bien las palabras con el léxico.
    - Reduce palabras exageradas (ej: 'hooooola' → 'hola').
    - Elimina espacios repetidos.

    En pocas palabras: deja el texto listo para analizarlo correctamente.
    """
    t = t.lower().strip()

    # Quitar tildes transformando caracteres Unicode
    t = ''.join(c for c in unicodedata.normalize('NFD', t)
                if unicodedata.category(c) != 'Mn')

    # Reducir repeticiones exageradas de caracteres
    t = re.sub(r'(.)\1{2,}', r'\1', t)

    # Normalizar espacios repetidos
    return re.sub(r'\s+', ' ', t)

def contiene(t: str, frases: list) -> bool:
    """
    Revisa si alguna frase importante aparece dentro del texto.

    Esto se usa especialmente para frases graves como 'no quiero vivir'
    o 'quitarme la vida'. Detectarlas automáticamente permite que el sistema
    marque el mensaje como riesgo alto al instante.
    """
    return any(f in t for f in frases)

# =========================================================
# LÓGICA DE ANÁLISIS DE SENTIMIENTO
# =========================================================

def senti_es(t: str) -> float:
    """
    Analiza el texto usando el mini-léxico español definido arriba.

    Recorre palabra por palabra y:
    - Suma puntos por palabras positivas.
    - Resta puntos por palabras negativas.

    Luego normaliza la puntuación a un rango entre -1.0 y 1.0.
    Es un análisis muy simple, pero ayuda a reforzar el puntaje de VADER.
    """
    p = 0
    for w in t.split():
        if w in LEXICO["pos"]:
            p += 1
        elif w in LEXICO["neg"]:
            p -= 1

    return max(-1, min(1, p / 5))


def analizar_nota(texto: str) -> dict:
    """
    Realiza el análisis principal del mensaje.

    Flujo de trabajo:
    1. Normaliza el texto.
    2. Busca frases extremas (relacionadas con suicidio).
    3. Si encuentra algo grave, clasifica como 'EXTREMO' sin analizar más.
    4. Si no, mezcla:
       - resultado de VADER
       - resultado del léxico español
    5. Con ese promedio decide si es POSITIVO, NEGATIVO o NEUTRO.

    Retorna un diccionario con:
    - 'clasificacion'  → resumen textual
    - 'puntuacion_compuesta' → número entre -1.0 y 1.0
    """
    t = norm(texto)

    extremo = [
        "suicidio", "suicidarme", "quitarme la vida", "terminar con mi vida",
        "no quiero vivir", "ya no quiero vivir", "quiero morir",
        "planeo morir", "voy a morir", "me quiero ir"
    ]

    # Regla inmediata: si hay frases de riesgo suicida
    if contiene(t, extremo):
        return {"clasificacion": "EXTREMO", "puntuacion_compuesta": -1.0}

    # Combina análisis de VADER + léxico español
    vader_score = sia.polarity_scores(texto)["compound"] if sia else 0.0
    punt = (vader_score + senti_es(t)) / 2

    # Decide categoría
    if punt >= 0.05:
        c = "POSITIVO"
    elif punt <= -0.05:
        c = "NEGATIVO"
    else:
        c = "NEUTRO"
        punt = 0.0  # Limpieza: si es neutro, la puntuación se pone en cero exacto

    return {"clasificacion": c, "puntuacion_compuesta": punt}

# =========================================================
# DETECCIÓN FINAL DE RIESGO
# =========================================================

def detectar_nivel_riesgo(texto: str, analisis: dict) -> str:
    """
    Determina el nivel de riesgo final usando el análisis anterior.

    ¿Cómo decide?

    - Nivel ALTO:
        * Si la clasificación es EXTREMO.
        * O si el texto contiene peticiones urgentes como 'auxilio' o 'no puedo más'.

    - Nivel MEDIO:
        * Si el sentimiento general es muy negativo (puntuación < -0.6).

    - Nivel BAJO:
        * Para todo lo demás.

    Es básicamente una capa adicional encargada de clasificar la urgencia del mensaje.
    """
    t = norm(texto)

    ayuda = [
        "ayuda", "socorro", "auxilio", "emergencia",
        "no puedo mas", "estoy al limite"
    ]

    if analisis["clasificacion"] == "EXTREMO" or contiene(t, ayuda):
        return "ALTO"

    if analisis["puntuacion_compuesta"] < -0.6:
        return "MEDIO"

    return "BAJO"

# =========================================================
# PRUEBA RÁPIDA
# =========================================================
# Si ejecutas este archivo directamente, se hacen unas pruebas rápidas
# para verificar que todo funcione como debería.

if __name__ == "__main__":
    ejemplos = [
        "Siento que ya no puedo más. He pensado en terminar con mi vida. Necesito ayuda.",
        "Estoy muy triste y no tengo ganas de nada",
        "Hoy me siento increíblemente feliz y agradecido",
        "Me siento fatal, estoy al limite, no se que hacer."
    ]
    
    print("\n--- INICIANDO PRUEBA DEL MOTOR DE ANÁLISIS ---")
    
    for t in ejemplos:
        a = analizar_nota(t)
        r = detectar_nivel_riesgo(t, a)

        print(f"\nTexto: {t}")
        print(f"  → Análisis: Clasificación='{a['clasificacion']}', Puntuación={a['puntuacion_compuesta']:.2f}")
        print(f"  → Riesgo Detectado: {r}")
