import streamlit as st


def obtener_rol_usuario():
    """
    Obtiene el rol del usuario actual desde session_state.
    Lo normaliza a minúsculas para evitar problemas con Admin/admin/ADMIN.
    """

    if "usuario" not in st.session_state:
        return None

    rol = st.session_state["usuario"].get("rol")

    if rol is None:
        return None

    return str(rol).strip().lower()


def usuario_es_admin():
    """
    Permite que admin/administrador nunca quede bloqueado por error.
    """

    rol_usuario = obtener_rol_usuario()

    if rol_usuario in ["admin", "administrador"]:
        return True

    return False


def puede_ver_pagina(conn, clave_pagina):
    """
    Consulta si el rol del usuario puede ver una página específica.
    """

    rol_usuario = obtener_rol_usuario()

    if rol_usuario is None:
        return False

    if usuario_es_admin():
        return True

    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT
                COALESCE(prp.puede_ver, FALSE)
            FROM roles r
            JOIN permisos_rol_pagina prp
                ON r.rol_id = prp.rol_id
            JOIN paginas_sistema p
                ON prp.pagina_id = p.pagina_id
            WHERE LOWER(r.clave) = LOWER(%s)
            AND p.clave = %s
            AND r.activo = TRUE
            AND p.activo = TRUE
            LIMIT 1;
        """, (
            rol_usuario,
            clave_pagina
        ))

        resultado = cursor.fetchone()

        if resultado is None:
            return False

        return bool(resultado[0])

    except Exception as e:

        st.error(f"Error al validar permisos: {e}")
        return False

    finally:

        cursor.close()


def validar_acceso_pagina(conn, clave_pagina):
    """
    Función principal que usarás en cada página.
    Si el usuario no tiene sesión, lo manda al login.
    Si no tiene permiso, bloquea la página.
    """

    if "usuario" not in st.session_state:
        st.switch_page("streamlit_app.py")

    if not puede_ver_pagina(conn, clave_pagina):
        st.error("No tienes permisos para esta sección.")
        st.stop()