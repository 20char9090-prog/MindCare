# =====================================
# db_manager.py
# =====================================
# Este archivo se encarga de manejar toda la interacción con la base de datos SQLite
# de MindCare. Aquí se crean las tablas, se registran usuarios, se guardan alertas
# y se consultan datos de manera segura.

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Ruta donde se guardará la base de datos
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "mindcare.db"

# =====================================
# Función para crear conexión a la DB
# =====================================
def create_connection() -> Optional[sqlite3.Connection]:
    """
    Crea y devuelve una conexión a la base de datos SQLite.

    Qué hace paso a paso:
    1. Asegura que la carpeta donde se guardará la DB exista.
    2. Intenta conectarse al archivo 'mindcare.db'.
    3. Activa las llaves foráneas para mantener consistencia de datos.
    4. Configura la conexión para devolver filas como diccionarios.
    5. Si hay un error, lo imprime y devuelve None.
    
    Devuelve:
    - Una conexión sqlite3.Connection si todo va bien.
    - None si ocurre algún error.
    """
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        # Asegurar que las tablas y columnas necesarias existan en la DB
        try:
            setup_db(conn)
        except Exception:
            # Si por alguna razón la inicialización falla, no interrumpimos la conexión
            pass
        return conn
    except sqlite3.Error as e:
        print(f"[DB] Error al conectar: {e}")
        return None

# =====================================
# Función para crear tablas si no existen
# =====================================
def setup_db(conn: sqlite3.Connection):
    """
    Crea las tablas 'usuarios' y 'alertas' si no existen.

    Qué hace:
    1. Tabla 'usuarios': guarda id, user_id, fecha de registro y último acceso.
    2. Tabla 'alertas': guarda las alertas con referencia al usuario,
       mensaje, clasificación, riesgo, puntuación y fecha de alerta.
    3. La tabla alertas tiene clave foránea hacia 'usuarios' para mantener
       integridad referencial.
    """
    with conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT UNIQUE NOT NULL,
                fecha_registro TEXT NOT NULL,
                ultimo_acceso TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alertas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                mensaje TEXT NOT NULL,
                clasificacion TEXT NOT NULL,
                riesgo TEXT NOT NULL,
                puntuacion REAL,
                valor REAL,
                fecha_alerta TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        # Asegurar columna 'valor' en bases de datos antiguas
        cur.execute("PRAGMA table_info(alertas)")
        cols = [row[1] for row in cur.fetchall()]
        if 'valor' not in cols:
            try:
                cur.execute("ALTER TABLE alertas ADD COLUMN valor REAL")
            except sqlite3.OperationalError:
                # Si falla por alguna razón, continuamos sin interrumpir
                pass

# =====================================
# Función para registrar un usuario
# =====================================
def registrar_usuario_y_obtener_id(user_uuid: str) -> int:
    """
    Registra un usuario en la base de datos si no existe y devuelve su ID.

    Cómo funciona:
    1. Intenta conectarse a la base de datos.
    2. Busca si el usuario ya existe por su 'user_id'.
       - Si existe, actualiza la fecha de último acceso.
       - Si no existe, lo inserta con fecha de registro y último acceso.
    3. Devuelve el ID interno del usuario (auto-incremental).
    4. Si hay problemas con la conexión, devuelve -1.
    
    Parámetro:
    - user_uuid: identificador único del usuario (por ejemplo, nombre de usuario)
    
    Retorna:
    - ID del usuario en la base de datos.
    """
    conn = create_connection()
    if conn is None:
        return -1

    now = datetime.now().isoformat()
    usuario_id = -1
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM usuarios WHERE user_id = ?", (user_uuid,))
        result = cur.fetchone()
        if result:
            usuario_id = int(result["id"])
            cur.execute("UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?", (now, usuario_id))
        else:
            cur.execute(
                "INSERT INTO usuarios (user_id, fecha_registro, ultimo_acceso) VALUES (?, ?, ?)",
                (user_uuid, now, now)
            )
            usuario_id = cur.lastrowid
    conn.close()
    return usuario_id

# =====================================
# Función para registrar alertas
# =====================================
def registrar_alerta(usuario_id: int, mensaje: str, analisis: Dict, riesgo: str, valor: float = None):
    """
    Guarda una alerta en la base de datos para un usuario específico.

    Qué hace:
    1. Conecta a la base de datos.
    2. Inserta en la tabla 'alertas' los siguientes datos:
       - usuario_id: referencia al usuario
       - mensaje: texto que envió el usuario
       - clasificación: resultado del análisis (positivo, negativo, extremo, neutro)
       - riesgo: nivel de riesgo detectado (BAJO, MEDIO, ALTO)
       - puntuación: valor numérico del análisis de sentimiento
       - fecha_alerta: momento en que se registró la alerta
    3. Cierra la conexión automáticamente.
    
    Parámetros:
    - usuario_id: ID del usuario en la DB
    - mensaje: texto del usuario
    - analisis: diccionario con 'clasificacion' y 'puntuacion_compuesta'
    - riesgo: nivel de riesgo detectado
    """
    conn = create_connection()
    if conn is None:
        return
    now = datetime.now().isoformat()
    with conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alertas (usuario_id, mensaje, clasificacion, riesgo, puntuacion, valor, fecha_alerta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario_id,
            mensaje,
            analisis.get("clasificacion", "NEUTRO"),
            riesgo,
            float(analisis.get("puntuacion_compuesta", analisis.get("puntuacion", 0.0) or 0.0)),
            float(valor) if valor is not None else (float(analisis.get("valor", 0.0)) if analisis.get("valor") is not None else None),
            now
        ))
    conn.close()

# =====================================
# Función para obtener todas las alertas de un usuario
# =====================================
def obtener_alertas(usuario_id: int) -> List[Dict]:
    """
    Devuelve todas las alertas de un usuario ordenadas de la más reciente a la más antigua.

    Cómo funciona:
    1. Se conecta a la base de datos.
    2. Hace un SELECT filtrando por usuario_id.
    3. Ordena los resultados por fecha de alerta descendente.
    4. Devuelve la lista de alertas como diccionarios.
    
    Parámetro:
    - usuario_id: ID del usuario en la DB
    
    Retorna:
    - Lista de diccionarios con keys: mensaje, clasificacion, riesgo, puntuacion, fecha_alerta
    """
    conn = create_connection()
    if conn is None:
        return []
    cur = conn.cursor()
    cur.execute("""
        SELECT mensaje, clasificacion, riesgo, puntuacion, valor, fecha_alerta
        FROM alertas
        WHERE usuario_id = ?
        ORDER BY fecha_alerta DESC
    """, (usuario_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# =====================================
# Función para obtener estadísticas y tendencia emocional
# =====================================
def obtener_stats_y_tendencia(usuario_id: int) -> dict:
    """
    Devuelve estadísticas y tendencia emocional para el usuario:
    - total_interacciones: total de alertas
    - ultimo_estado: última clasificación
    - tendencia_emocional: lista de {fecha, valor}
    """
    conn = create_connection()
    if conn is None:
        return {
            "total_interacciones": 0,
            "ultimo_estado": "-",
            "tendencia_emocional": []
        }
    cur = conn.cursor()
    cur.execute("""
        SELECT clasificacion, puntuacion, fecha_alerta, riesgo
        FROM alertas
        WHERE usuario_id = ?
        ORDER BY fecha_alerta ASC
    """, (usuario_id,))
    rows = cur.fetchall()
    conn.close()
    total = len(rows)
    ultimo_estado = rows[-1]["clasificacion"] if rows else "-"
    ultimo_riesgo = rows[-1]["riesgo"] if rows else "-"
    tendencia = [
        {"fecha": row["fecha_alerta"], "valor": row["puntuacion"]}
        for row in rows
    ]
    return {
        "total_interacciones": total,
        "ultimo_estado": ultimo_estado,
        "ultimo_riesgo": ultimo_riesgo,
        "tendencia_emocional": tendencia
    }

# =====================================
# Inicialización directa de la DB
# =====================================
if __name__ == "__main__":
    """
    Permite inicializar la base de datos ejecutando este archivo directamente.
    Crea las tablas si no existen y muestra un mensaje de confirmación.
    """
    conn = create_connection()
    if conn:
        setup_db(conn)
        conn.close()
        print("Base de datos inicializada correctamente.")
