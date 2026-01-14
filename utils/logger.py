from utils.conexionASupabase import get_connection

def registrar_log(usuario, accion, descripcion):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO logs (
            usuario_id,
            usuario_nombre,
            accion,
            descripcion,
            fecha
        )
        VALUES (%s, %s, %s, %s, NOW())
    """, (
        usuario["id"],
        usuario["nombre"],
        accion,
        descripcion
    ))

    conn.commit()
    conn.close()
