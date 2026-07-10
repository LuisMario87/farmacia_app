from utils.conexionASupabase import get_connection


def registrar_log(usuario, accion, descripcion):
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor()

        usuario_id = (
            usuario.get("id")
            or usuario.get("usuario_id")
        )

        usuario_nombre = usuario.get("nombre", "Usuario desconocido")

        cursor.execute("""
            INSERT INTO logs_auditoria (
                usuario_id,
                usuario_nombre,
                accion,
                descripcion,
                fecha
            )
            VALUES (%s, %s, %s, %s, NOW())
        """, (
            usuario_id,
            usuario_nombre,
            accion,
            descripcion
        ))

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()

        print(f"Error al registrar log: {e}")

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()