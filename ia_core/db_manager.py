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
                ultimo_acceso TEXT NOT NULL,
                telegram_id TEXT,
                telegram_opt_in INTEGER DEFAULT 0,
                ultimo_envio_notificacion TEXT
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telegram_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                fecha_creacion TEXT NOT NULL
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
        # Asegurar columnas nuevas en usuarios para compatibilidad con DB antiguas
        cur.execute("PRAGMA table_info(usuarios)")
        user_cols = [row[1] for row in cur.fetchall()]
        if 'telegram_id' not in user_cols:
            try:
                cur.execute("ALTER TABLE usuarios ADD COLUMN telegram_id TEXT")
            except sqlite3.OperationalError:
                pass
        if 'telegram_opt_in' not in user_cols:
            try:
                cur.execute("ALTER TABLE usuarios ADD COLUMN telegram_opt_in INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
        if 'ultimo_envio_notificacion' not in user_cols:
            try:
                cur.execute("ALTER TABLE usuarios ADD COLUMN ultimo_envio_notificacion TEXT")
            except sqlite3.OperationalError:
                pass
        # Añadir columna opcional para nombre para mostrar (display_name)
        if 'display_name' not in user_cols:
            try:
                cur.execute("ALTER TABLE usuarios ADD COLUMN display_name TEXT")
            except sqlite3.OperationalError:
                pass
        # Asegurar columnas para autenticación
        if 'password_hash' not in user_cols:
            try:
                cur.execute("ALTER TABLE usuarios ADD COLUMN password_hash TEXT")
            except sqlite3.OperationalError:
                pass
        if 'password_salt' not in user_cols:
            try:
                cur.execute("ALTER TABLE usuarios ADD COLUMN password_salt TEXT")
            except sqlite3.OperationalError:
                pass

        # Tabla para sesiones (tokens de sesión)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expiry TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)
        # Tabla para almacenar mensajes de chat (usuario y asistente)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                sender TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                analisis TEXT,
                fecha TEXT NOT NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE
            )
        """)

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


def registrar_contacto_telegram(user_uuid: str, telegram_id: str, opt_in: bool) -> int:
    """
    Registra o actualiza el contacto de Telegram para un usuario.
    Devuelve el usuario_id interno.
    """
    usuario_id = registrar_usuario_y_obtener_id(user_uuid)
    conn = create_connection()
    if conn is None:
        return usuario_id
    with conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE usuarios SET telegram_id = ?, telegram_opt_in = ? WHERE id = ?",
            (telegram_id, 1 if opt_in else 0, usuario_id)
        )
    conn.close()
    return usuario_id


def registrar_o_actualizar_usuario(user_uuid: str, display_name: str = None) -> int:
    """
    Registra un usuario si no existe y opcionalmente actualiza su `display_name`.

    - user_uuid: identificador único persistente (por ejemplo uuid del cliente)
    - display_name: nombre legible que mostrará la UI / notificaciones

    Devuelve el usuario_id interno en la DB o -1 si falla la conexión.
    """
    usuario_id = registrar_usuario_y_obtener_id(user_uuid)
    if usuario_id == -1:
        return -1
    if display_name is not None:
        conn = create_connection()
        if conn is None:
            return usuario_id
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE usuarios SET display_name = ? WHERE id = ?", (display_name, usuario_id))
        conn.close()
    return usuario_id


def obtener_usuario_id_por_userid_o_displayname(identifier: str) -> int:
    """
    Busca un usuario por su `user_id` o por su `display_name`.
    Devuelve el `id` interno si existe, o -1 si no se encuentra o hay error.
    """
    conn = create_connection()
    if conn is None:
        return -1
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE user_id = ? OR display_name = ? LIMIT 1", (identifier, identifier))
    row = cur.fetchone()
    conn.close()
    if not row:
        return -1
    return int(row['id'])


### -----------------------------
### Autenticación y sesiones
### -----------------------------
import os
import hashlib
import binascii
import uuid
from datetime import timedelta


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 200000)
    return binascii.hexlify(dk).decode('ascii')


def set_user_password(user_uuid: str, password: str) -> bool:
    """Registra el usuario si hace falta y guarda el hash+salt de la contraseña."""
    usuario_id = registrar_usuario_y_obtener_id(user_uuid)
    if usuario_id == -1:
        return False
    salt = os.urandom(16)
    pwd_hash = _hash_password(password, salt)
    conn = create_connection()
    if conn is None:
        return False
    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET password_hash = ?, password_salt = ? WHERE id = ?",
                    (pwd_hash, binascii.hexlify(salt).decode('ascii'), usuario_id))
    conn.close()
    return True


def verify_user_password(user_uuid: str, password: str) -> int:
    """Verifica la contraseña. Devuelve usuario_id si válida, o -1 si no válida/No existe."""
    conn = create_connection()
    if conn is None:
        return -1
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash, password_salt FROM usuarios WHERE user_id = ?", (user_uuid,))
    row = cur.fetchone()
    conn.close()
    if not row or not row['password_hash'] or not row['password_salt']:
        return -1
    salt = binascii.unhexlify(row['password_salt'].encode('ascii'))
    expected = row['password_hash']
    if _hash_password(password, salt) == expected:
        return int(row['id'])
    return -1


def create_session(usuario_id: int, hours_valid: int = 24) -> str:
    """Crea un token de sesión válido por `hours_valid` horas y lo guarda en DB."""
    token = str(uuid.uuid4())
    expiry = (datetime.now() + timedelta(hours=hours_valid)).isoformat()
    conn = create_connection()
    if conn is None:
        return ''
    with conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO sessions (usuario_id, token, expiry) VALUES (?, ?, ?)", (usuario_id, token, expiry))
    conn.close()
    return token


def validate_session(token: str) -> int:
    """Valida token de sesión; devuelve usuario_id o -1 si inválido/expirado."""
    conn = create_connection()
    if conn is None:
        return -1
    cur = conn.cursor()
    cur.execute("SELECT usuario_id, expiry FROM sessions WHERE token = ?", (token,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return -1
    expiry = datetime.fromisoformat(row['expiry'])
    if datetime.now() > expiry:
        # sesión expirada; eliminarla
        with conn:
            cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.close()
        return -1
    usuario_id = int(row['usuario_id'])
    conn.close()
    return usuario_id


def delete_session(token: str) -> bool:
    conn = create_connection()
    if conn is None:
        return False
    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.close()
    return True


def crear_codigo_telegram(user_uuid: str, code: str) -> bool:
    """Crea un código temporal para vincular una cuenta Telegram con user_uuid."""
    conn = create_connection()
    if conn is None:
        return False
    now = datetime.now().isoformat()
    with conn:
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO telegram_codes (user_id, code, fecha_creacion) VALUES (?, ?, ?)", (user_uuid, code, now))
        except sqlite3.IntegrityError:
            # código ya existe
            conn.close()
            return False
    conn.close()
    return True


def consumir_codigo_telegram(code: str):
    """Consume (obtiene y borra) el código, devolviendo el user_id o None."""
    conn = create_connection()
    if conn is None:
        return None
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM telegram_codes WHERE code = ?", (code,))
        row = cur.fetchone()
        if not row:
            return None
        user_id = row["user_id"]
        cur.execute("DELETE FROM telegram_codes WHERE code = ?", (code,))
    conn.close()
    return user_id


def obtener_telegram_y_optin(usuario_id: int):
    """Devuelve (telegram_id, opt_in, ultimo_envio_notificacion) o (None, 0, None)."""
    conn = create_connection()
    if conn is None:
        return (None, 0, None)
    cur = conn.cursor()
    cur.execute("SELECT telegram_id, telegram_opt_in, ultimo_envio_notificacion FROM usuarios WHERE id = ?", (usuario_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return (None, 0, None)
    return (row["telegram_id"], int(row["telegram_opt_in"] or 0), row["ultimo_envio_notificacion"])


def actualizar_ultima_notificacion(usuario_id: int):
    """Guarda la marca temporal del último envío de notificación para rate limiting."""
    conn = create_connection()
    if conn is None:
        return
    now = datetime.now().isoformat()
    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE usuarios SET ultimo_envio_notificacion = ? WHERE id = ?", (now, usuario_id))
    conn.close()

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


def guardar_mensaje(usuario_id: int, sender: str, mensaje: str, analisis: Dict = None):
    """Guarda un mensaje de chat en la tabla `mensajes`. `sender` puede ser 'user' o 'assistant'."""
    conn = create_connection()
    if conn is None:
        return
    now = datetime.now().isoformat()
    analisis_json = None
    try:
        if analisis is not None:
            import json as _json
            analisis_json = _json.dumps(analisis)
    except Exception:
        analisis_json = None
    with conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO mensajes (usuario_id, sender, mensaje, analisis, fecha) VALUES (?, ?, ?, ?, ?)",
            (usuario_id, sender, mensaje, analisis_json, now)
        )
    conn.close()


def obtener_mensajes(usuario_id: int, limit: int = 100):
    """Devuelve los últimos `limit` mensajes del usuario ordenados asc por fecha."""
    conn = create_connection()
    if conn is None:
        return []
    cur = conn.cursor()
    cur.execute(
        "SELECT sender, mensaje, analisis, fecha FROM mensajes WHERE usuario_id = ? ORDER BY fecha ASC LIMIT ?",
        (usuario_id, limit)
    )
    rows = cur.fetchall()
    conn.close()
    # Convert rows to dicts
    results = []
    import json as _json
    for r in rows:
        anal = None
        try:
            anal = _json.loads(r['analisis']) if r['analisis'] else None
        except Exception:
            anal = None
        results.append({
            'sender': r['sender'],
            'mensaje': r['mensaje'],
            'analisis': anal,
            'fecha': r['fecha']
        })
    return results


def obtener_mensajes_por_usuario_ids(usuario_ids: list, limit: int = 500):
    """Devuelve mensajes combinados de varios `usuario_id` ordenados asc por fecha."""
    if not usuario_ids:
        return []
    conn = create_connection()
    if conn is None:
        return []
    # Preparar placeholders
    placeholders = ','.join('?' for _ in usuario_ids)
    cur = conn.cursor()
    query = f"SELECT sender, mensaje, analisis, fecha FROM mensajes WHERE usuario_id IN ({placeholders}) ORDER BY fecha ASC LIMIT ?"
    params = list(usuario_ids) + [limit]
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    results = []
    import json as _json
    for r in rows:
        anal = None
        try:
            anal = _json.loads(r['analisis']) if r['analisis'] else None
        except Exception:
            anal = None
        results.append({
            'sender': r['sender'],
            'mensaje': r['mensaje'],
            'analisis': anal,
            'fecha': r['fecha']
        })
    return results


def obtener_usuario_ids_por_display_name(display_name: str) -> list:
    """Devuelve lista de ids de usuarios cuyo `display_name` coincide exactamente."""
    conn = create_connection()
    if conn is None:
        return []
    cur = conn.cursor()
    cur.execute("SELECT id, user_id FROM usuarios WHERE display_name = ?", (display_name,))
    rows = cur.fetchall()
    conn.close()
    return [int(r['id']) for r in rows]


def obtener_usuario_id_por_userid_exacto(user_uuid: str) -> int:
    """Busca un usuario por `user_id` exacto sin crear ninguno nuevo. Devuelve id o -1."""
    conn = create_connection()
    if conn is None:
        return -1
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuarios WHERE user_id = ? LIMIT 1", (user_uuid,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return -1
    return int(row['id'])


def transferir_mensajes(from_usuario_ids: list, to_usuario_id: int):
    """Mueve mensajes de una lista de `from_usuario_ids` hacia `to_usuario_id`.

    Retorna el número de filas afectadas.
    """
    if not from_usuario_ids or to_usuario_id is None:
        return 0
    conn = create_connection()
    if conn is None:
        return 0
    total = 0
    with conn:
        cur = conn.cursor()
        for fid in from_usuario_ids:
            try:
                cur.execute("UPDATE mensajes SET usuario_id = ? WHERE usuario_id = ?", (to_usuario_id, fid))
                total += cur.rowcount
            except Exception:
                # continuar con los demás
                pass
    conn.close()
    return total


def backup_db(suffix: str = None) -> str:
    """Crea una copia de seguridad del archivo de la base de datos y devuelve la ruta del backup.
    Si `suffix` no se provee, se añade marca temporal.
    """
    try:
        import shutil
        from datetime import datetime as _dt

        if suffix is None:
            suffix = _dt.now().strftime('%Y%m%dT%H%M%S')
        dst = DB_PATH.with_name(f"{DB_PATH.stem}.bak-{suffix}{DB_PATH.suffix}")
        shutil.copy2(str(DB_PATH), str(dst))
        return str(dst)
    except Exception:
        return ''

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
