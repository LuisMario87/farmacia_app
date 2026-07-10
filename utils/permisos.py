import streamlit as st


def obtener_rol_usuario():
    if "usuario" not in st.session_state:
        return None

    rol = st.session_state["usuario"].get("rol")

    if rol is None:
        return None

    return str(rol).strip().lower()


def puede_ver_pagina(conn, clave_pagina):
    rol_usuario = obtener_rol_usuario()

    if rol_usuario is None:
        return False

    # Seguridad extra:
    # El admin nunca queda bloqueado accidentalmente.
    if rol_usuario in ["admin", "administrador"]:
        return True

    query = """
        SELECT
            prp.puede_ver
        FROM permisos_rol_pagina prp
        JOIN roles r
            ON prp.rol_id = r.rol_id
        JOIN paginas_sistema p
            ON prp.pagina_id = p.pagina_id
        WHERE LOWER(r.clave) = LOWER(%s)
        AND p.clave = %s
        AND r.activo = TRUE
        AND p.activo = TRUE
        LIMIT 1;
    """

    cursor = conn.cursor()
    cursor.execute(query, (rol_usuario, clave_pagina))
    resultado = cursor.fetchone()
    cursor.close()

    if resultado is None:
        return False

    return bool(resultado[0])


def validar_acceso_pagina(conn, clave_pagina):
    if "usuario" not in st.session_state:
        st.switch_page("streamlit_app.py")

    if not puede_ver_pagina(conn, clave_pagina):
        st.error("No tienes permisos para esta sección.")
        st.stop()