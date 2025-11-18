# =====================================
# admin_mindcare.py
# =====================================
# Este archivo permite visualizar los datos de la base de datos
# de MindCare directamente desde la consola.
# Muestra:
# - Usuarios registrados
# - Alertas registradas
# Puede mostrar tablas en formato "fancy" si está instalado 'tabulate',
# o en formato simple si no está disponible.

import sqlite3
import os

# =====================================
# Intento de importar 'tabulate'
# =====================================
# Si la librería 'tabulate' está instalada, se usan tablas más bonitas.
# Si no, se muestra un aviso y se usa un formato básico.
try:
    from tabulate import tabulate
    USAR_TABULATE = True
except ImportError:
    USAR_TABULATE = False
    print("\n  Nota: 'tabulate' no está instalado. Mostrando tablas en formato simple.")
    print("Para mejores tablas puedes instalarlo con:  pip install tabulate\n")

# =====================================
# Ruta de la base de datos
# =====================================
DB_PATH = os.path.join(os.path.dirname(__file__), "mindcare.db")

# =====================================
# Función para conectar a la DB
# =====================================
def conectar():
    """
    Conecta a la base de datos SQLite y devuelve la conexión.
    
    Retorna:
    - sqlite3.Connection
    """
    return sqlite3.connect(DB_PATH)

# =====================================
# Función para mostrar todos los usuarios
# =====================================
def ver_usuarios():
    """
    Muestra en consola todos los usuarios registrados.

    Qué hace paso a paso:
    1. Se conecta a la base de datos.
    2. Hace un SELECT de todos los usuarios ordenados por ID.
    3. Cierra la conexión.
    4. Imprime un encabezado con título de sección.
    5. Si no hay usuarios, muestra un mensaje indicando que no hay registros.
    6. Si hay usuarios:
       - Si 'tabulate' está instalado, imprime una tabla bonita.
       - Si no, imprime los datos en formato simple.
    """
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, user_id, fecha_registro, ultimo_acceso
        FROM usuarios
        ORDER BY id ASC
    """)

    datos = cursor.fetchall()
    conn.close()

    print("\n===============================")
    print("  🧑‍💻 USUARIOS REGISTRADOS")
    print("===============================\n")

    if not datos:
        print("No hay usuarios registrados.\n")
        return

    headers = ["ID", "USER_UUID", "REGISTRO", "ULTIMO ACCESO"]

    if USAR_TABULATE:
        print(tabulate(datos, headers=headers, tablefmt="fancy_grid"))
    else:
        print(headers)
        for fila in datos:
            print(fila)
    print()

# =====================================
# Función para mostrar todas las alertas
# =====================================
def ver_alertas():
    """
    Muestra en consola todas las alertas registradas.

    Qué hace paso a paso:
    1. Se conecta a la base de datos.
    2. Hace un SELECT de todas las alertas,
       uniéndolas con la tabla de usuarios para obtener el user_id.
    3. Ordena las alertas por fecha descendente.
    4. Cierra la conexión.
    5. Imprime un encabezado con título de sección.
    6. Si no hay alertas, indica que no hay registros.
    7. Si hay alertas:
       - Si 'tabulate' está disponible, imprime tabla bonita.
       - Si no, imprime los datos en formato simple.
    """
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT a.id, u.user_id, a.mensaje, a.clasificacion,
               a.riesgo, a.puntuacion, a.fecha_alerta
        FROM alertas a
        JOIN usuarios u ON u.id = a.usuario_id
        ORDER BY a.fecha_alerta DESC
    """)

    datos = cursor.fetchall()
    conn.close()

    print("\n===============================")
    print("  🚨 ALERTAS REGISTRADAS")
    print("===============================\n")

    if not datos:
        print("No hay alertas registradas.\n")
        return

    headers = ["ID", "USER_UUID", "MENSAJE", "CLASIF", "RIESGO", "PUNTUACIÓN", "FECHA"]

    if USAR_TABULATE:
        print(tabulate(datos, headers=headers, tablefmt="fancy_grid"))
    else:
        print(headers)
        for fila in datos:
            print(fila)
    print()

# =====================================
# Main: Ejecutar funciones al correr el script
# =====================================
if __name__ == "__main__":
    ver_usuarios()
    ver_alertas()
