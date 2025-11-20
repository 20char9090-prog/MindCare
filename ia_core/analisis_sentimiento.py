import re
import unicodedata
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from typing import Dict, List, Tuple
from difflib import SequenceMatcher
import logging

# =========================================================
# CONFIGURACIÓN INICIAL Y LÉXICOS
# =========================================================
try:
    sia = SentimentIntensityAnalyzer()
except LookupError:
    print("⚠️  Ejecuta: nltk.download('vader_lexicon')")
    sia = None

LEXICO = {
    "pos": [
        "feliz", "alegre", "contento", "tranquilo", "bien", "optimista",
        "esperanza", "motivado", "amor", "paz", "gratitud", "confianza",
        "energia", "entusiasmo", "satisfecho", "orgulloso", "genial",
        "excelente", "maravilloso", "fantastico", "increible", "mejor"
    ],
    "neg": [
        "triste", "mal", "fatal", "horrible", "enojado", "rabia", "derrotado",
        "estresado", "ansioso", "desesperado", "vacio", "solo", "perdido",
        "agobiado", "abrumado", "miedo", "panico", "culpa", "verguenza",
        "deprimido", "preocupado", "frustrado", "dolor", "sufrimiento"
    ],
    "neutro": [
        "normal", "regular", "equilibrado", "estable", "ok", "ahi",
        "igual", "comun", "nada especial", "sin mas", "neutral"
    ]
}

# =========================================================
# FUNCIONES AUXILIARES
# =========================================================
def norm(t: str) -> str:
    """Normaliza texto: minúsculas, sin acentos, sin repeticiones excesivas"""
    t = t.lower().strip()
    t = ''.join(c for c in unicodedata.normalize('NFD', t) 
                if unicodedata.category(c) != 'Mn')
    t = re.sub(r'(.)\1{2,}', r'\1', t)  # "hoooola" -> "hola"
    return re.sub(r'\s+', ' ', t)

# =========================================================
# PATRONES DE RIESGO EXTREMO
# =========================================================

# Palabras clave que SIEMPRE indican riesgo extremo
PALABRAS_CRITICAS = [
    "suicidio", "suicidarme", "suicida", "matarme", "matar me"
]

# Frases completas de riesgo extremo
FRASES_EXTREMAS = [
    # Ideación suicida directa
    "quitarme la vida", "quitar me la vida",
    "terminar con mi vida", "terminar con todo",
    "acabar con mi vida", "acabar conmigo",
    "no quiero vivir", "ya no quiero vivir", "no quiero vivir mas",
    "quiero morir", "quiero morirme", 
    "planeo morir", "voy a morir",
    "no quiero existir", "ya no quiero existir",
    "no quiero estar aqui", "no quiero estar aca",
    
    # Deseo de desaparecer
    "quiero desaparecer", "quisiera desaparecer",
    "ojala no despertara", "ojala no despertar", "ojala no despierto",
    "ojala no existiera", "ojala no existir",
    "preferiria estar muerto", "preferiria estar muerta",
    "preferiria no vivir", "prefiero no vivir",
    "prefiero estar muerto", "prefiero estar muerta",
    
    # Pérdida de sentido
    "no quiero seguir viviendo", "ya no quiero seguir viviendo",
    "no puedo seguir viviendo", "ya no puedo seguir viviendo",
    "no quiero esta vida", "ya no quiero esta vida",
    "mi vida no tiene sentido", "no le veo sentido a mi vida",
    "no veo razon para vivir", "no hay razon para vivir",
    "no vale la pena vivir",
    
    # Planificación
    "pensando en matarme", "pienso en matarme",
    "estoy listo para morir", "estoy lista para morir",
    "ya tome la decision",
    
    # Agotamiento vital
    "no puedo mas con mi vida", "no puedo mas vivir",
    "cansado de vivir", "cansada de vivir",
    "ya no deseo vivir", "no deseo vivir",
    
    # Deseo de cesación
    "quiero dejar de existir", "dejar de existir",
    "quiero que todo termine", "quiero que mi vida termine",
    "no quiero seguir asi", "ya no quiero seguir asi"
]

# Normalizamos todas las frases
FRASES_EXTREMAS_NORM = [norm(f) for f in FRASES_EXTREMAS]
PALABRAS_CRITICAS_NORM = [norm(p) for p in PALABRAS_CRITICAS]

def similitud(a: str, b: str) -> float:
    """Calcula similitud entre dos strings (0.0 a 1.0)"""
    return SequenceMatcher(None, a, b).ratio()

def buscar_con_typos(texto: str, patrones: List[str], umbral: float = 0.85) -> List[str]:
    """
    Busca patrones permitiendo errores ortográficos.
    Retorna lista de coincidencias encontradas.
    """
    encontradas = []
    palabras_texto = texto.split()
    
    for patron in patrones:
        palabras_patron = patron.split()
        n_patron = len(palabras_patron)
        
        # Buscar ventanas deslizantes del tamaño del patrón
        for i in range(len(palabras_texto) - n_patron + 1):
            ventana = " ".join(palabras_texto[i:i + n_patron])
            sim = similitud(ventana, patron)
            
            if sim >= umbral:
                encontradas.append(f"'{patron}' (similitud: {sim:.2f}, encontrado: '{ventana}')")
    
    return encontradas

def contiene_contenido_extremo(texto_normalizado: str) -> Tuple[bool, List[str]]:
    """
    Detecta contenido de riesgo extremo con tolerancia a typos.
    Retorna: (es_extremo, lista_de_coincidencias)
    """
    encontradas = []
    
    # 1. Verificar palabras críticas (exactas)
    for palabra in PALABRAS_CRITICAS_NORM:
        if palabra in texto_normalizado:
            encontradas.append(f"CRÍTICO: '{palabra}'")
    
    # 2. Verificar frases extremas (exactas)
    for frase in FRASES_EXTREMAS_NORM:
        if frase in texto_normalizado:
            encontradas.append(f"'{frase}'")
    
    # 3. Si no hay coincidencias exactas, buscar con tolerancia a typos
    if not encontradas:
        # Frases más críticas para buscar con fuzzy matching
        frases_criticas_principales = [
            "no quiero vivir",
            "no quiero vivir mas",
            "quiero morir",
            "me quiero matar",
            "no quiero existir",
            "no quiero estar aqui",
            "terminar con mi vida",
            "acabar con mi vida",
            "quitarme la vida"
        ]
        
        coincidencias_fuzzy = buscar_con_typos(texto_normalizado, frases_criticas_principales, umbral=0.85)
        if coincidencias_fuzzy:
            encontradas.append("🔍 Detección con corrección de typos:")
            encontradas.extend(coincidencias_fuzzy)
    
    # 4. Patrones con regex para mayor flexibilidad (permite pequeñas variaciones)
    patrones_criticos = [
        (r'\bno\s+[a-z]{0,2}quiero\s+vivir', "no quiero vivir"),
        (r'\b[a-z]{0,2}quiero\s+morir', "quiero morir"),
        (r'\bno\s+[a-z]{0,2}quiero\s+estar\s+(aqui|aca)', "no quiero estar aquí"),
        (r'\bno\s+[a-z]{0,2}quiero\s+existir', "no quiero existir"),
        (r'\btermin(ar|o)\s+(con\s+)?(mi\s+vida|todo)', "terminar con mi vida"),
        (r'\bacab(ar|o)\s+(con\s+)?(mi\s+vida|conmigo)', "acabar con mi vida"),
        (r'\b[a-z]{0,2}matar\s*me\b', "matarme"),
        (r'\bquit(ar|o)\s*me\s+la\s+vida', "quitarme la vida"),
    ]
    
    for patron, descripcion in patrones_criticos:
        if re.search(patron, texto_normalizado):
            encontradas.append(f"PATRÓN: '{descripcion}'")
    
    return (len(encontradas) > 0, encontradas)

# =========================================================
# ANÁLISIS DE SENTIMIENTO
# =========================================================
def senti_es(t: str) -> float:
    """Análisis simple basado en léxico español"""
    palabras = t.split()
    if not palabras:
        return 0.0
    
    p = 0
    neutro_detectado = False
    
    for w in palabras:
        if w in LEXICO["pos"]:
            p += 1
        elif w in LEXICO["neg"]:
            p -= 1
        elif w in LEXICO["neutro"]:
            neutro_detectado = True
    
    # Si detectamos palabras neutras explícitas, retornamos 0
    if neutro_detectado and abs(p) <= 1:
        return 0.0
    
    # Normalizar por longitud del texto
    if p == 0:
        return 0.0
    
    factor = max(5, len(palabras) / 3)
    return max(-1, min(1, p / factor))

def analizar_nota(texto: str) -> Dict:
    """
    Analiza el sentimiento de un texto.
    Retorna: {clasificacion, puntuacion_compuesta, contenido_extremo}
    """
    if not texto or not texto.strip():
        return {
            "clasificacion": "NEUTRO",
            "puntuacion_compuesta": 0.0,
            "contenido_extremo": []
        }
    
    t = norm(texto)
    
    # Detección extrema MEJORADA
    es_extremo, coincidencias = contiene_contenido_extremo(t)
    if es_extremo:
        return {
            "clasificacion": "EXTREMO",
            "puntuacion_compuesta": -1.0,
            "contenido_extremo": coincidencias
        }
    
    # Análisis de sentimiento combinado
    vader_score = sia.polarity_scores(texto)["compound"] if sia else 0.0
    lexico_score = senti_es(t)
    
    # Ponderación: VADER (40%) + Léxico ES (60%)
    punt = (vader_score * 0.4) + (lexico_score * 0.6)
    
    # Clasificación con umbrales más precisos
    if punt >= 0.1:
        c = "POSITIVO"
    elif punt <= -0.1:
        c = "NEGATIVO"
    else:
        c = "NEUTRO"
        punt = 0.0
    
    return {
        "clasificacion": c,
        "puntuacion_compuesta": round(punt, 3),
        "contenido_extremo": []
    }

# =========================================================
# DETECCIÓN DE RIESGO
# =========================================================
def detectar_nivel_riesgo(texto: str, analisis: Dict) -> Tuple[str, List[str], int]:
    """
    Retorna: (nivel_riesgo, motivos, valor_riesgo)
    Niveles: ALTO, MEDIO, BAJO
    Valores: ALTO=3, MEDIO=2, BAJO=1
    """
    if not texto or not texto.strip():
        logging.debug("Texto vacío o sin contenido relevante.")
        return ("BAJO", [], 1)

    t = norm(texto)
    motivos = []

    logging.debug(f"Texto normalizado: {t}")
    logging.debug(f"Análisis recibido: {analisis}")

    # ============================================
    # PRIORIDAD 1: RIESGO ALTO
    # ============================================

    # 1A. Clasificación extrema del análisis
    if analisis.get("clasificacion") == "EXTREMO":
        motivos.append("⚠️  IDEACIÓN SUICIDA DETECTADA")
        if analisis.get("contenido_extremo"):
            for coincidencia in analisis["contenido_extremo"][:3]:
                motivos.append(f"  → {coincidencia}")
        logging.debug("Riesgo ALTO detectado por clasificación extrema.")
        return ("ALTO", motivos, 3)

    # 1B. Doble verificación: buscar contenido extremo directamente
    es_extremo, coincidencias = contiene_contenido_extremo(t)
    if es_extremo:
        motivos.append("⚠️  CONTENIDO DE ALTO RIESGO")
        for coincidencia in coincidencias[:3]:
            motivos.append(f"  → {coincidencia}")
        logging.debug("Riesgo ALTO detectado por contenido extremo.")
        return ("ALTO", motivos, 3)

    # ============================================
    # PRIORIDAD 2: RIESGO MEDIO
    # ============================================
    frases_medio_riesgo = [
        "no quiero seguir", "quisiera desaparecer", "estoy cansado de todo",
        "me siento vacío", "no encuentro sentido", "estoy agotado", "no puedo más",
        "me siento perdido", "todo está mal", "no sé qué hacer"
    ]
    for frase in frases_medio_riesgo:
        if frase in t:
            motivos.append("⚠️  FRASES DE RIESGO MEDIO DETECTADAS")
            motivos.append(f"  → {frase}")
            logging.debug("Riesgo MEDIO detectado por frases de riesgo medio.")
            return ("MEDIO", motivos, 2)

    # ============================================
    # PRIORIDAD 3: RIESGO BAJO
    # ============================================
    motivos.append("✅  Sin indicadores de riesgo significativos detectados.")
    logging.debug("Riesgo BAJO detectado. Sin indicadores significativos.")
    return ("BAJO", motivos, 1)

# =========================================================
# GENERAR RECOMENDACIÓN
# =========================================================
def generar_recomendacion(nivel_riesgo: str) -> str:
    """Retorna una recomendación basada en el nivel de riesgo"""
    recomendaciones = {
        "ALTO": """
🚨 ACCIÓN INMEDIATA REQUERIDA:
- Contactar línea de prevención del suicidio: [Número local]
- No dejar a la persona sola
- Buscar atención profesional de emergencia
- Eliminar medios de autolesión del entorno
        """.strip(),
        
        "MEDIO": """
⚠️  ATENCIÓN RECOMENDADA:
- Sugerir apoyo profesional (psicólogo/psiquiatra)
- Mantener comunicación cercana
- Validar sentimientos y ofrecer escucha activa
- Recursos de apoyo disponibles 24/7
        """.strip(),
        
        "BAJO": """
✓ SEGUIMIENTO NORMAL:
- Continuar con apoyo empático
- Monitorear cambios en el estado emocional
- Recordar recursos de apoyo disponibles
        """.strip()
    }
    
    return recomendaciones.get(nivel_riesgo, "")

# =========================================================
# FUNCIÓN PRINCIPAL DE ANÁLISIS COMPLETO
# =========================================================
def analisis_completo(texto: str) -> Dict:
    """
    Realiza un análisis completo del texto.
    Retorna diccionario con todos los resultados.
    """
    analisis = analizar_nota(texto)
    nivel_riesgo, motivos, valor_riesgo = detectar_nivel_riesgo(texto, analisis)
    recomendacion = generar_recomendacion(nivel_riesgo)

    return {
        "texto_original": texto,
        "texto_normalizado": norm(texto),
        "sentimiento": {
            "clasificacion": analisis["clasificacion"],
            "puntuacion": analisis["puntuacion_compuesta"],
            "contenido_extremo": analisis.get("contenido_extremo", [])
        },
        "riesgo": {
            "nivel": nivel_riesgo,
            "motivos": motivos,
            "valor": valor_riesgo,
            "recomendacion": recomendacion
        }
    }

# =========================================================
# PRUEBA RÁPIDA CON TUS EJEMPLOS
# =========================================================
if __name__ == "__main__":
    ejemplos = [
        "no quieor vivir mas", 
        "no quiero estar aqui",
        "no quiero vivir mas",
        "Ya no quiero existir",
        "Siento que ya no puedo más. He pensado en terminar con mi vida.",
        "Estoy muy triste y no tengo ganas de nada",
        "Hoy me siento increíblemente feliz y agradecido",
        "Me siento fatal, estoy al limite, no se que hacer.",
        "Estoy un poco ansioso por el examen de mañana",
        "Necesito ayuda urgente, no puedo mas con esto",
        "quiero morir",
        "me quiero matar",
        # MENSAJES NEUTROS
        "Me siento tranquilo hoy, nada especial",
        "Hoy fue un día normal",
        "Estoy bien, nada fuera de lo común",
        "Me siento equilibrado",
        "Estoy ok, solo cansado del día",
        "Hoy fue regular",
        "Estoy ahí, sin más"
    ]
    
    print("\n" + "="*70)
    print("SISTEMA DE ANÁLISIS DE SENTIMIENTOS Y DETECCIÓN DE RIESGO")
    print("="*70)
    
    for i, texto in enumerate(ejemplos, 1):
        resultado = analisis_completo(texto)
        
        print(f"\n[{i}] Texto: '{texto}'")
        print(f"    Normalizado: '{resultado['texto_normalizado']}'")
        print(f"    Sentimiento: {resultado['sentimiento']['clasificacion']} "
              f"({resultado['sentimiento']['puntuacion']:.3f})")
        print(f"    Riesgo: {resultado['riesgo']['nivel']}")
        
        if resultado['riesgo']['motivos']:
            print(f"    Motivos:")
            for motivo in resultado['riesgo']['motivos']:
                print(f"      {motivo}")
    
    print("\n" + "="*70)
    print("✓ Análisis completado")
    print("="*70 + "\n")