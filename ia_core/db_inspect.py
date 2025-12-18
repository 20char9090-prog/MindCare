import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "mindcare.db"

out = {"ok": False, "db_path": str(DB_PATH), "error": None}
try:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Usuarios
    cur.execute("SELECT id, user_id, display_name FROM usuarios")
    users = [dict(r) for r in cur.fetchall()]

    # Conteo mensajes por usuario
    cur.execute("SELECT usuario_id, COUNT(*) as cnt FROM mensajes GROUP BY usuario_id")
    counts = {int(r['usuario_id']): int(r['cnt']) for r in cur.fetchall()}

    # Buscar usuarios relacionados con 'Camila' (por user_id o display_name)
    target = 'Camila'
    cur.execute("SELECT id, user_id, display_name FROM usuarios WHERE user_id = ? OR display_name = ?", (target, target))
    camila_users = [dict(r) for r in cur.fetchall()]

    camila_messages = {}
    for u in camila_users:
        uid = int(u['id'])
        cur.execute("SELECT sender, mensaje, analisis, fecha FROM mensajes WHERE usuario_id = ? ORDER BY fecha ASC", (uid,))
        camila_messages[uid] = [dict(r) for r in cur.fetchall()]

    out.update({
        "ok": True,
        "users": users,
        "message_counts": counts,
        "camila_users": camila_users,
        "camila_messages": camila_messages
    })
    conn.close()
except Exception as e:
    out['error'] = str(e)

print(json.dumps(out, ensure_ascii=False, indent=2))
