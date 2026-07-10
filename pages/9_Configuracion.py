import streamlit as st
import pandas as pd
import bcrypt
import re
import unicodedata

from utils.conexionASupabase import get_connection
from utils.logger import registrar_log


st.set_page_config(
    page_title="Configuración",
    layout="wide"
)

# ===============================
# SEGURIDAD
# ===============================

if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

rol_usuario = st.session_state["usuario"]["rol"].strip().lower()

roles_permitidos = [
    "admin",
    "administrador"
]

if rol_usuario not in roles_permitidos:
    st.error("No tienes permisos para esta sección")
    st.stop()


# ===============================
# CONEXIÓN
# ===============================

conn = get_connection()
cursor = conn.cursor()


# ===============================
# FUNCIONES AUXILIARES
# ===============================

def registrar_log_seguro(usuario, accion, descripcion):
    try:
        registrar_log(
            usuario,
            accion,
            descripcion
        )
    except Exception:
        pass


def generar_clave(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-z0-9]+", "_", texto)
    texto = texto.strip("_")
    return texto


def inicializar_tablas_roles_permisos(conn):
    cursor_local = conn.cursor()

    try:
        cursor_local.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                rol_id SERIAL PRIMARY KEY,
                clave VARCHAR(50) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                descripcion TEXT,
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cursor_local.execute("""
            CREATE TABLE IF NOT EXISTS paginas_sistema (
                pagina_id SERIAL PRIMARY KEY,
                clave VARCHAR(100) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                ruta VARCHAR(200),
                orden INTEGER DEFAULT 0,
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)

        cursor_local.execute("""
            CREATE TABLE IF NOT EXISTS permisos_rol_pagina (
                permiso_id SERIAL PRIMARY KEY,
                rol_id INTEGER REFERENCES roles(rol_id) ON DELETE CASCADE,
                pagina_id INTEGER REFERENCES paginas_sistema(pagina_id) ON DELETE CASCADE,
                puede_ver BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (rol_id, pagina_id)
            );
        """)

        cursor_local.execute("""
            INSERT INTO roles
            (
                clave,
                nombre,
                descripcion,
                activo
            )
            VALUES
            (
                'admin',
                'Administrador',
                'Acceso completo al sistema',
                TRUE
            ),
            (
                'empleado',
                'Empleado',
                'Acceso operativo limitado',
                TRUE
            )
            ON CONFLICT (clave) DO NOTHING;
        """)

        cursor_local.execute("""
            INSERT INTO roles
            (
                clave,
                nombre,
                descripcion,
                activo
            )
            SELECT DISTINCT
                LOWER(TRIM(rol)) AS clave,
                INITCAP(LOWER(TRIM(rol))) AS nombre,
                'Rol existente importado desde usuarios' AS descripcion,
                TRUE AS activo
            FROM usuarios
            WHERE rol IS NOT NULL
            AND TRIM(rol) <> ''
            ON CONFLICT (clave) DO NOTHING;
        """)

        cursor_local.execute("""
            INSERT INTO paginas_sistema
            (
                clave,
                nombre,
                ruta,
                orden,
                activo
            )
            VALUES
            (
                'dashboard',
                'Dashboard',
                'pages/1_Dashboard_Farmacias.py',
                1,
                TRUE
            ),
            (
                'consulta_financiera',
                'Consulta Financiera',
                'pages/2_Consulta_Financiera.py',
                2,
                TRUE
            ),
            (
                'registros',
                'Registros',
                'pages/3_Registros.py',
                3,
                TRUE
            ),
            (
                'administracion_facturas',
                'Administración de Facturas',
                'pages/4_Administracion_Facturas.py',
                4,
                TRUE
            ),
            (
                'configuracion',
                'Configuración',
                'pages/9_Configuracion.py',
                5,
                TRUE
            )
            ON CONFLICT (clave) DO UPDATE SET
                nombre = EXCLUDED.nombre,
                ruta = EXCLUDED.ruta,
                orden = EXCLUDED.orden,
                activo = TRUE;
        """)

        cursor_local.execute("""
            INSERT INTO permisos_rol_pagina
            (
                rol_id,
                pagina_id,
                puede_ver
            )
            SELECT
                r.rol_id,
                p.pagina_id,
                TRUE
            FROM roles r
            CROSS JOIN paginas_sistema p
            WHERE r.clave IN ('admin', 'administrador')
            ON CONFLICT (rol_id, pagina_id)
            DO UPDATE SET
                puede_ver = TRUE;
        """)

        cursor_local.execute("""
            INSERT INTO permisos_rol_pagina
            (
                rol_id,
                pagina_id,
                puede_ver
            )
            SELECT
                r.rol_id,
                p.pagina_id,
                CASE
                    WHEN p.clave IN (
                        'dashboard',
                        'registros',
                        'administracion_facturas'
                    )
                    THEN TRUE
                    ELSE FALSE
                END
            FROM roles r
            CROSS JOIN paginas_sistema p
            WHERE r.clave = 'empleado'
            ON CONFLICT (rol_id, pagina_id)
            DO NOTHING;
        """)

        conn.commit()

    except Exception as e:
        conn.rollback()
        st.error(f"Error al inicializar roles y permisos: {e}")

    finally:
        cursor_local.close()


def cargar_roles_activos(conn):
    return pd.read_sql("""
        SELECT
            clave,
            nombre
        FROM roles
        WHERE activo = TRUE
        ORDER BY nombre;
    """, conn)


def cargar_roles_todos(conn):
    return pd.read_sql("""
        SELECT
            rol_id,
            clave,
            nombre,
            descripcion,
            activo
        FROM roles
        ORDER BY nombre;
    """, conn)


def limpiar_texto(valor):
    if pd.isna(valor) or valor is None or str(valor).strip() == "":
        return ""

    return str(valor)


# Inicializa tablas de roles/permisos automáticamente
inicializar_tablas_roles_permisos(conn)


# ===============================
# INTERFAZ
# ===============================

st.title("Configuración")

tab1, tab2, tab3 = st.tabs([
    "Gestión de usuarios",
    "Gestión de farmacias",
    "Logs"
])


# ==================================================
# TAB 1 - GESTIÓN DE USUARIOS
# ==================================================

with tab1:

    st.subheader("Gestión de usuarios")

    tab_crear_usuario, tab_admin_usuarios, tab_roles_permisos = st.tabs([
        "Crear usuario",
        "Administrar usuarios",
        "Roles y permisos"
    ])

    # ==================================================
    # CREAR USUARIO
    # ==================================================

    with tab_crear_usuario:

        st.subheader("Crear nuevo usuario")

        df_roles_activos = cargar_roles_activos(conn)

        if df_roles_activos.empty:

            st.warning("No hay roles activos disponibles. Primero crea un rol.")

        else:

            roles_claves = df_roles_activos["clave"].tolist()

            roles_nombres = {
                row["clave"]: row["nombre"]
                for _, row in df_roles_activos.iterrows()
            }

            with st.form("config_form_crear_usuario", clear_on_submit=True):

                nombre = st.text_input(
                    "Nombre completo",
                    key="config_crear_usuario_nombre"
                )

                email = st.text_input(
                    "Correo",
                    key="config_crear_usuario_email"
                )

                password = st.text_input(
                    "Contraseña",
                    type="password",
                    key="config_crear_usuario_password"
                )

                rol = st.selectbox(
                    "Rol",
                    roles_claves,
                    format_func=lambda x: roles_nombres.get(x, x),
                    key="config_crear_usuario_rol"
                )

                crear_usuario = st.form_submit_button(
                    "Crear usuario",
                    use_container_width=True
                )

            if crear_usuario:

                if not nombre.strip() or not email.strip() or not password.strip():

                    st.warning("Completa todos los campos.")

                else:

                    try:

                        cursor.execute("""
                            SELECT COUNT(*)
                            FROM usuarios
                            WHERE LOWER(email) = LOWER(%s)
                        """, (
                            email.strip(),
                        ))

                        existe_usuario = cursor.fetchone()[0]

                        if existe_usuario > 0:

                            st.warning("Ya existe un usuario con ese correo.")

                        else:

                            password_hash = bcrypt.hashpw(
                                password.encode(),
                                bcrypt.gensalt()
                            ).decode()

                            cursor.execute("""
                                INSERT INTO usuarios
                                (
                                    nombre,
                                    email,
                                    password_hash,
                                    rol
                                )
                                VALUES
                                (
                                    %s,
                                    %s,
                                    %s,
                                    %s
                                )
                            """, (
                                nombre.strip(),
                                email.strip(),
                                password_hash,
                                rol
                            ))

                            conn.commit()

                            registrar_log_seguro(
                                st.session_state["usuario"],
                                "ALTA_USUARIO",
                                f"Creó el usuario {nombre.strip()} con rol {rol}"
                            )

                            st.success("Usuario creado correctamente.")

                            st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(f"Error: {e}")

    # ==================================================
    # ADMINISTRAR USUARIOS
    # ==================================================

    with tab_admin_usuarios:

        st.subheader("Administrar usuarios")

        df_users = pd.read_sql("""
            SELECT
                usuario_id,
                nombre,
                email,
                rol
            FROM usuarios
            ORDER BY nombre
        """, conn)

        if df_users.empty:

            st.info("No hay usuarios registrados.")

        else:

            st.dataframe(
                df_users,
                use_container_width=True,
                hide_index=True
            )

            st.divider()

            usuarios_dict = {
                int(row["usuario_id"]): f"{row['nombre']} ({row['email']})"
                for _, row in df_users.iterrows()
            }

            usuario_sel = st.selectbox(
                "Selecciona un usuario",
                list(usuarios_dict.keys()),
                format_func=lambda x: usuarios_dict[x],
                key="config_usuario_seleccionado"
            )

            user_data = df_users[
                df_users["usuario_id"] == usuario_sel
            ].iloc[0]

            df_roles_activos = cargar_roles_activos(conn)

            roles_claves = df_roles_activos["clave"].tolist()

            roles_nombres = {
                row["clave"]: row["nombre"]
                for _, row in df_roles_activos.iterrows()
            }

            rol_actual_usuario = str(user_data["rol"]).strip().lower()

            if rol_actual_usuario not in roles_claves:
                roles_claves.insert(0, rol_actual_usuario)
                roles_nombres[rol_actual_usuario] = rol_actual_usuario

            st.markdown("### Editar usuario")

            with st.form(f"config_form_editar_usuario_{usuario_sel}"):

                col1, col2 = st.columns(2)

                with col1:

                    nuevo_nombre = st.text_input(
                        "Nombre",
                        value=user_data["nombre"],
                        key=f"config_editar_usuario_nombre_{usuario_sel}"
                    )

                    nuevo_email = st.text_input(
                        "Correo",
                        value=user_data["email"],
                        key=f"config_editar_usuario_email_{usuario_sel}"
                    )

                with col2:

                    nuevo_rol = st.selectbox(
                        "Rol",
                        roles_claves,
                        index=roles_claves.index(rol_actual_usuario),
                        format_func=lambda x: roles_nombres.get(x, x),
                        key=f"config_editar_usuario_rol_{usuario_sel}"
                    )

                    cambiar_pass = st.checkbox(
                        "Cambiar contraseña",
                        key=f"config_editar_usuario_cambiar_pass_{usuario_sel}"
                    )

                    nueva_pass = ""

                    if cambiar_pass:

                        nueva_pass = st.text_input(
                            "Nueva contraseña",
                            type="password",
                            key=f"config_editar_usuario_nueva_pass_{usuario_sel}"
                        )

                guardar_cambios = st.form_submit_button(
                    "Guardar cambios",
                    use_container_width=True
                )

            if guardar_cambios:

                if not nuevo_nombre.strip() or not nuevo_email.strip():

                    st.warning("Nombre y correo son obligatorios.")

                elif cambiar_pass and not nueva_pass.strip():

                    st.warning("Ingresa la nueva contraseña.")

                else:

                    try:

                        cursor.execute("""
                            SELECT COUNT(*)
                            FROM usuarios
                            WHERE LOWER(email) = LOWER(%s)
                            AND usuario_id <> %s
                        """, (
                            nuevo_email.strip(),
                            usuario_sel
                        ))

                        existe_email = cursor.fetchone()[0]

                        if existe_email > 0:

                            st.warning("Ya existe otro usuario con ese correo.")

                        else:

                            if cambiar_pass:

                                password_hash = bcrypt.hashpw(
                                    nueva_pass.encode(),
                                    bcrypt.gensalt()
                                ).decode()

                                cursor.execute("""
                                    UPDATE usuarios
                                    SET
                                        nombre = %s,
                                        email = %s,
                                        rol = %s,
                                        password_hash = %s
                                    WHERE usuario_id = %s
                                """, (
                                    nuevo_nombre.strip(),
                                    nuevo_email.strip(),
                                    nuevo_rol,
                                    password_hash,
                                    usuario_sel
                                ))

                            else:

                                cursor.execute("""
                                    UPDATE usuarios
                                    SET
                                        nombre = %s,
                                        email = %s,
                                        rol = %s
                                    WHERE usuario_id = %s
                                """, (
                                    nuevo_nombre.strip(),
                                    nuevo_email.strip(),
                                    nuevo_rol,
                                    usuario_sel
                                ))

                            conn.commit()

                            registrar_log_seguro(
                                st.session_state["usuario"],
                                "MODIFICACION_USUARIO",
                                f"Modificó el usuario ID {usuario_sel}"
                            )

                            st.success("Usuario actualizado correctamente.")

                            st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(f"Error: {e}")

            st.divider()

            st.markdown("### Eliminar usuario")

            usuario_actual_id = (
                st.session_state["usuario"].get("id")
                or st.session_state["usuario"].get("usuario_id")
            )

            if usuario_sel == usuario_actual_id:

                st.warning("No puedes eliminar tu propio usuario.")

            else:

                confirmar_eliminar = st.checkbox(
                    "Confirmo que quiero eliminar este usuario",
                    key=f"config_confirmar_eliminar_usuario_{usuario_sel}"
                )

                if st.button(
                    "Eliminar usuario",
                    use_container_width=True,
                    disabled=not confirmar_eliminar,
                    key=f"config_eliminar_usuario_{usuario_sel}"
                ):

                    try:

                        cursor.execute("""
                            DELETE FROM usuarios
                            WHERE usuario_id = %s
                        """, (
                            usuario_sel,
                        ))

                        conn.commit()

                        registrar_log_seguro(
                            st.session_state["usuario"],
                            "ELIMINACION_USUARIO",
                            f"Eliminó el usuario ID {usuario_sel}"
                        )

                        st.success("Usuario eliminado correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(f"Error: {e}")

    # ==================================================
    # ROLES Y PERMISOS
    # ==================================================

    with tab_roles_permisos:

        st.subheader("Roles y permisos")

        df_roles = cargar_roles_todos(conn)

        df_paginas = pd.read_sql("""
            SELECT
                pagina_id,
                clave,
                nombre,
                ruta,
                orden,
                activo
            FROM paginas_sistema
            WHERE activo = TRUE
            ORDER BY orden, nombre;
        """, conn)

        # -------------------------------
        # CREAR NUEVO ROL
        # -------------------------------

        with st.expander("Crear nuevo rol", expanded=False):

            with st.form("config_form_crear_rol", clear_on_submit=True):

                nombre_rol = st.text_input(
                    "Nombre del rol",
                    placeholder="Ej. Supervisor, Auditor, Encargado",
                    key="config_nombre_nuevo_rol"
                )

                descripcion_rol = st.text_area(
                    "Descripción",
                    placeholder="Describe para qué se usará este rol.",
                    key="config_descripcion_nuevo_rol"
                )

                crear_rol = st.form_submit_button(
                    "Crear rol",
                    use_container_width=True
                )

            if crear_rol:

                clave_rol = generar_clave(nombre_rol)

                if not nombre_rol.strip():

                    st.warning("El nombre del rol es obligatorio.")

                elif not clave_rol:

                    st.warning("El nombre del rol no es válido.")

                else:

                    try:

                        cursor.execute("""
                            SELECT COUNT(*)
                            FROM roles
                            WHERE clave = %s
                        """, (
                            clave_rol,
                        ))

                        existe_rol = cursor.fetchone()[0]

                        if existe_rol > 0:

                            st.warning("Ya existe un rol con ese nombre.")

                        else:

                            cursor.execute("""
                                INSERT INTO roles
                                (
                                    clave,
                                    nombre,
                                    descripcion,
                                    activo
                                )
                                VALUES
                                (
                                    %s,
                                    %s,
                                    %s,
                                    TRUE
                                )
                                RETURNING rol_id;
                            """, (
                                clave_rol,
                                nombre_rol.strip(),
                                descripcion_rol.strip()
                            ))

                            nuevo_rol_id = cursor.fetchone()[0]

                            for _, pagina in df_paginas.iterrows():

                                cursor.execute("""
                                    INSERT INTO permisos_rol_pagina
                                    (
                                        rol_id,
                                        pagina_id,
                                        puede_ver
                                    )
                                    VALUES
                                    (
                                        %s,
                                        %s,
                                        FALSE
                                    )
                                    ON CONFLICT (rol_id, pagina_id)
                                    DO NOTHING;
                                """, (
                                    int(nuevo_rol_id),
                                    int(pagina["pagina_id"])
                                ))

                            conn.commit()

                            registrar_log_seguro(
                                st.session_state["usuario"],
                                "ALTA_ROL",
                                f"Creó el rol {nombre_rol.strip()}"
                            )

                            st.success("Rol creado correctamente.")

                            st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(f"Error: {e}")

        st.divider()

        # -------------------------------
        # ROLES EXISTENTES
        # -------------------------------

        st.markdown("### Roles existentes")

        if df_roles.empty:

            st.info("No hay roles registrados.")

        else:

            df_roles_mostrar = df_roles.copy()

            df_roles_mostrar["activo"] = df_roles_mostrar["activo"].apply(
                lambda x: "ACTIVO" if x else "INACTIVO"
            )

            df_roles_mostrar = df_roles_mostrar.rename(columns={
                "rol_id": "ID",
                "clave": "Clave",
                "nombre": "Nombre",
                "descripcion": "Descripción",
                "activo": "Estado"
            })

            st.dataframe(
                df_roles_mostrar,
                use_container_width=True,
                hide_index=True
            )

        st.divider()

        # -------------------------------
        # CONFIGURAR PERMISOS
        # -------------------------------

        st.markdown("### Configurar permisos por rol")

        if df_roles.empty or df_paginas.empty:

            st.info("Primero debes tener roles y páginas registradas.")

        else:

            roles_dict = {
                int(row["rol_id"]): f"{row['nombre']} ({row['clave']})"
                for _, row in df_roles.iterrows()
            }

            rol_id_sel = st.selectbox(
                "Selecciona un rol",
                options=list(roles_dict.keys()),
                format_func=lambda x: roles_dict[x],
                key="config_rol_permiso_sel"
            )

            rol_data = df_roles[
                df_roles["rol_id"] == rol_id_sel
            ].iloc[0]

            rol_clave = str(rol_data["clave"]).lower()

            try:

                for _, pagina in df_paginas.iterrows():

                    cursor.execute("""
                        INSERT INTO permisos_rol_pagina
                        (
                            rol_id,
                            pagina_id,
                            puede_ver
                        )
                        VALUES
                        (
                            %s,
                            %s,
                            FALSE
                        )
                        ON CONFLICT (rol_id, pagina_id)
                        DO NOTHING;
                    """, (
                        int(rol_id_sel),
                        int(pagina["pagina_id"])
                    ))

                conn.commit()

            except Exception as e:

                conn.rollback()

                st.error(f"Error al preparar permisos: {e}")

            df_permisos = pd.read_sql("""
                SELECT
                    p.pagina_id,
                    p.clave,
                    p.nombre,
                    p.ruta,
                    COALESCE(prp.puede_ver, FALSE) AS puede_ver
                FROM paginas_sistema p
                LEFT JOIN permisos_rol_pagina prp
                    ON p.pagina_id = prp.pagina_id
                    AND prp.rol_id = %s
                WHERE p.activo = TRUE
                ORDER BY p.orden, p.nombre;
            """, conn, params=(int(rol_id_sel),))

            st.info("Marca las páginas que este rol podrá visualizar.")

            if rol_clave in ["admin", "administrador"]:

                st.warning(
                    "El rol administrador tiene acceso completo por seguridad. "
                    "Aunque cambies permisos aquí, no se recomienda bloquearlo."
                )

            with st.form(f"config_form_permisos_rol_{rol_id_sel}"):

                nuevo_nombre_rol = st.text_input(
                    "Nombre del rol",
                    value=str(rol_data["nombre"]),
                    key=f"config_editar_nombre_rol_{rol_id_sel}"
                )

                nueva_descripcion_rol = st.text_area(
                    "Descripción del rol",
                    value=limpiar_texto(rol_data["descripcion"]),
                    key=f"config_editar_descripcion_rol_{rol_id_sel}"
                )

                permisos_nuevos = {}

                st.markdown("#### Páginas visibles")

                for _, pagina in df_permisos.iterrows():

                    permisos_nuevos[int(pagina["pagina_id"])] = st.checkbox(
                        pagina["nombre"],
                        value=bool(pagina["puede_ver"]),
                        key=f"permiso_rol_{rol_id_sel}_pagina_{pagina['pagina_id']}"
                    )

                estado_rol = st.selectbox(
                    "Estado del rol",
                    [
                        "ACTIVO",
                        "INACTIVO"
                    ],
                    index=0 if bool(rol_data["activo"]) else 1,
                    key=f"estado_rol_{rol_id_sel}",
                    disabled=rol_clave in ["admin", "administrador"]
                )

                guardar_permisos = st.form_submit_button(
                    "Guardar cambios del rol",
                    use_container_width=True
                )

            if guardar_permisos:

                if not nuevo_nombre_rol.strip():

                    st.warning("El nombre del rol es obligatorio.")

                else:

                    try:

                        for pagina_id, puede_ver in permisos_nuevos.items():

                            cursor.execute("""
                                INSERT INTO permisos_rol_pagina
                                (
                                    rol_id,
                                    pagina_id,
                                    puede_ver
                                )
                                VALUES
                                (
                                    %s,
                                    %s,
                                    %s
                                )
                                ON CONFLICT (rol_id, pagina_id)
                                DO UPDATE SET
                                    puede_ver = EXCLUDED.puede_ver;
                            """, (
                                int(rol_id_sel),
                                int(pagina_id),
                                bool(puede_ver)
                            ))

                        if rol_clave in ["admin", "administrador"]:

                            cursor.execute("""
                                UPDATE roles
                                SET
                                    nombre = %s,
                                    descripcion = %s,
                                    activo = TRUE
                                WHERE rol_id = %s
                            """, (
                                nuevo_nombre_rol.strip(),
                                nueva_descripcion_rol.strip(),
                                int(rol_id_sel)
                            ))

                        else:

                            cursor.execute("""
                                UPDATE roles
                                SET
                                    nombre = %s,
                                    descripcion = %s,
                                    activo = %s
                                WHERE rol_id = %s
                            """, (
                                nuevo_nombre_rol.strip(),
                                nueva_descripcion_rol.strip(),
                                estado_rol == "ACTIVO",
                                int(rol_id_sel)
                            ))

                        conn.commit()

                        registrar_log_seguro(
                            st.session_state["usuario"],
                            "MODIFICACION_PERMISOS_ROL",
                            f"Actualizó permisos del rol {rol_data['nombre']}"
                        )

                        st.success("Rol y permisos actualizados correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(f"Error: {e}")


# ==================================================
# TAB 2 - GESTIÓN DE FARMACIAS
# ==================================================

with tab2:

    st.subheader("Gestión de farmacias")

    # ---------------------------------
    # CARGAR FARMACIAS
    # ---------------------------------

    df_farmacias = pd.read_sql(
        """
        SELECT
            farmacia_id,
            nombre,
            ciudad,
            estado
        FROM farmacias
        ORDER BY nombre
        """,
        conn
    )

    # =================================
    # REGISTRO DE NUEVA FARMACIA
    # =================================

    st.subheader("Registrar nueva farmacia")

    with st.form("config_form_nueva_farmacia", clear_on_submit=True):

        nombre = st.text_input(
            "Nombre de la farmacia",
            key="config_nombre_nueva_farmacia"
        )

        ciudad = st.text_input(
            "Ciudad",
            key="config_ciudad_nueva_farmacia"
        )

        submitted = st.form_submit_button(
            "Guardar farmacia",
            use_container_width=True
        )

        if submitted:

            if not nombre.strip() or not ciudad.strip():

                st.error("Nombre y ciudad son obligatorios.")

            else:

                try:

                    cursor.execute(
                        """
                        INSERT INTO farmacias (
                            nombre,
                            ciudad,
                            estado
                        )
                        VALUES (%s, %s, %s)
                        """,
                        (
                            nombre.strip(),
                            ciudad.strip(),
                            "ACTIVA"
                        )
                    )

                    conn.commit()

                    registrar_log_seguro(
                        st.session_state["usuario"],
                        "ALTA_FARMACIA",
                        f"Registró la farmacia {nombre.strip()}"
                    )

                    st.success("Farmacia registrada correctamente.")

                    st.rerun()

                except Exception as e:

                    conn.rollback()

                    st.error(f"Error al registrar: {e}")

    st.divider()

    # =================================
    # LISTADO + EDICIÓN
    # =================================

    st.subheader("Farmacias registradas")

    if df_farmacias.empty:

        st.info("No hay farmacias registradas.")

    else:

        mostrar = st.radio(
            "Mostrar",
            [
                "Primeras 20",
                "Primeras 100",
                "Todas"
            ],
            horizontal=True,
            key="config_mostrar_farmacias"
        )

        if mostrar == "Primeras 20":

            df_view = df_farmacias.head(20)

        elif mostrar == "Primeras 100":

            df_view = df_farmacias.head(100)

        else:

            df_view = df_farmacias

        for _, row in df_view.iterrows():

            estado_actual = row["estado"] if row["estado"] else "ACTIVA"

            estado_icono = "🟢" if estado_actual == "ACTIVA" else "🔴"

            with st.expander(
                f"{estado_icono} {row['nombre']} ({row['ciudad']})"
            ):

                col1, col2, col3 = st.columns(3)

                nuevo_nombre = col1.text_input(
                    "Nombre",
                    value=row["nombre"],
                    key=f"config_nombre_farmacia_{row['farmacia_id']}"
                )

                nueva_ciudad = col2.text_input(
                    "Ciudad",
                    value=row["ciudad"],
                    key=f"config_ciudad_farmacia_{row['farmacia_id']}"
                )

                nuevo_estado = col3.selectbox(
                    "Estado",
                    [
                        "ACTIVA",
                        "CERRADA"
                    ],
                    index=0 if estado_actual == "ACTIVA" else 1,
                    key=f"config_estado_farmacia_{row['farmacia_id']}"
                )

                c1, c2 = st.columns(2)

                with c1:

                    if st.button(
                        "Actualizar",
                        key=f"config_actualizar_farmacia_{row['farmacia_id']}",
                        use_container_width=True
                    ):

                        if not nuevo_nombre.strip() or not nueva_ciudad.strip():

                            st.error("Nombre y ciudad son obligatorios.")

                        else:

                            try:

                                cursor.execute(
                                    """
                                    UPDATE farmacias
                                    SET
                                        nombre = %s,
                                        ciudad = %s,
                                        estado = %s
                                    WHERE farmacia_id = %s
                                    """,
                                    (
                                        nuevo_nombre.strip(),
                                        nueva_ciudad.strip(),
                                        nuevo_estado,
                                        row["farmacia_id"]
                                    )
                                )

                                conn.commit()

                                registrar_log_seguro(
                                    st.session_state["usuario"],
                                    "MODIFICACION_FARMACIA",
                                    f"Modificó la farmacia ID {row['farmacia_id']}"
                                )

                                st.success("Farmacia actualizada correctamente.")

                                st.rerun()

                            except Exception as e:

                                conn.rollback()

                                st.error(f"Error al actualizar: {e}")

                with c2:

                    if estado_actual == "ACTIVA":

                        if st.button(
                            "Cerrar farmacia",
                            key=f"config_cerrar_farmacia_{row['farmacia_id']}",
                            use_container_width=True
                        ):

                            try:

                                cursor.execute(
                                    """
                                    UPDATE farmacias
                                    SET estado = 'CERRADA'
                                    WHERE farmacia_id = %s
                                    """,
                                    (
                                        row["farmacia_id"],
                                    )
                                )

                                conn.commit()

                                registrar_log_seguro(
                                    st.session_state["usuario"],
                                    "CIERRE_FARMACIA",
                                    f"Cerró la farmacia ID {row['farmacia_id']}"
                                )

                                st.success("Farmacia marcada como cerrada.")

                                st.rerun()

                            except Exception as e:

                                conn.rollback()

                                st.error(f"Error: {e}")

                    else:

                        if st.button(
                            "Reabrir farmacia",
                            key=f"config_reabrir_farmacia_{row['farmacia_id']}",
                            use_container_width=True
                        ):

                            try:

                                cursor.execute(
                                    """
                                    UPDATE farmacias
                                    SET estado = 'ACTIVA'
                                    WHERE farmacia_id = %s
                                    """,
                                    (
                                        row["farmacia_id"],
                                    )
                                )

                                conn.commit()

                                registrar_log_seguro(
                                    st.session_state["usuario"],
                                    "REAPERTURA_FARMACIA",
                                    f"Reabrió la farmacia ID {row['farmacia_id']}"
                                )

                                st.success("Farmacia reactivada correctamente.")

                                st.rerun()

                            except Exception as e:

                                conn.rollback()

                                st.error(f"Error: {e}")


# ==================================================
# TAB 3 - LOGS
# ==================================================

with tab3:

    st.subheader("Logs del sistema")

    # ===============================
    # CARGA DE DATOS
    # ===============================

    df_logs = pd.read_sql("""
        SELECT
            log_id,
            usuario_nombre,
            accion,
            descripcion,
            fecha
        FROM logs_auditoria
        ORDER BY fecha DESC;
    """, conn)

    if df_logs.empty:

        st.info("Todavía no hay logs registrados en el sistema.")

    else:

        df_logs["fecha"] = pd.to_datetime(
            df_logs["fecha"],
            errors="coerce"
        )

        # ===============================
        # RESUMEN RÁPIDO
        # ===============================

        st.markdown("### Resumen rápido")

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Total de logs",
                len(df_logs)
            )

        with col2:

            st.metric(
                "Usuarios únicos",
                df_logs["usuario_nombre"].nunique()
            )

        with col3:

            st.metric(
                "Acciones distintas",
                df_logs["accion"].nunique()
            )

        st.divider()

        # ===============================
        # FILTROS
        # ===============================

        st.markdown("### Filtros")

        usuarios = (
            ["Todos"] +
            sorted(df_logs["usuario_nombre"].dropna().unique().tolist())
        )

        acciones = (
            ["Todas"] +
            sorted(df_logs["accion"].dropna().unique().tolist())
        )

        anios = (
            ["Todos"] +
            sorted(df_logs["fecha"].dropna().dt.year.unique().tolist(), reverse=True)
        )

        meses = (
            ["Todos"] +
            sorted(df_logs["fecha"].dropna().dt.month.unique().tolist())
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            usuario_sel = st.selectbox(
                "Usuario",
                usuarios,
                key="config_logs_usuario"
            )

        with col2:

            accion_sel = st.selectbox(
                "Acción",
                acciones,
                key="config_logs_accion"
            )

        with col3:

            anio_sel = st.selectbox(
                "Año",
                anios,
                key="config_logs_anio"
            )

        with col4:

            mes_sel = st.selectbox(
                "Mes",
                meses,
                key="config_logs_mes"
            )

        col1, col2 = st.columns([3, 1])

        with col1:

            busqueda = st.text_input(
                "Buscar en descripción",
                placeholder="Ej. venta, gasto, proveedor, factura...",
                key="config_logs_busqueda"
            )

        with col2:

            page_size = st.selectbox(
                "Filas por página",
                [
                    10,
                    25,
                    50,
                    100
                ],
                index=1,
                key="config_logs_page_size"
            )

        # ===============================
        # APLICAR FILTROS
        # ===============================

        df_filt = df_logs.copy()

        if usuario_sel != "Todos":

            df_filt = df_filt[
                df_filt["usuario_nombre"] == usuario_sel
            ]

        if accion_sel != "Todas":

            df_filt = df_filt[
                df_filt["accion"] == accion_sel
            ]

        if anio_sel != "Todos":

            df_filt = df_filt[
                df_filt["fecha"].dt.year == int(anio_sel)
            ]

        if mes_sel != "Todos":

            df_filt = df_filt[
                df_filt["fecha"].dt.month == int(mes_sel)
            ]

        if busqueda.strip():

            df_filt = df_filt[
                df_filt["descripcion"]
                .astype(str)
                .str.contains(
                    busqueda.strip(),
                    case=False,
                    na=False
                )
            ]

        # ===============================
        # PAGINACIÓN
        # ===============================

        total = len(df_filt)

        total_pages = max(
            1,
            (total - 1) // int(page_size) + 1
        )

        if "config_logs_page" not in st.session_state:
            st.session_state["config_logs_page"] = 1

        if st.session_state["config_logs_page"] > total_pages:
            st.session_state["config_logs_page"] = 1

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:

            page = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages,
                value=st.session_state["config_logs_page"],
                step=1,
                key="config_logs_page"
            )

        with col2:

            st.metric(
                "Resultados",
                total
            )

        with col3:

            st.caption(
                f"Página {page} de {total_pages}. "
                f"Mostrando máximo {page_size} registros."
            )

        start = (int(page) - 1) * int(page_size)
        end = start + int(page_size)

        # ===============================
        # TABLA
        # ===============================

        st.markdown("### Registros de actividad")

        if df_filt.empty:

            st.info("No hay logs que coincidan con los filtros seleccionados.")

        else:

            df_mostrar = df_filt.iloc[start:end].copy()

            df_mostrar["fecha"] = df_mostrar["fecha"].dt.strftime(
                "%d/%m/%Y %H:%M"
            )

            df_mostrar = df_mostrar.rename(columns={
                "log_id": "ID",
                "usuario_nombre": "Usuario",
                "accion": "Acción",
                "descripcion": "Descripción",
                "fecha": "Fecha"
            })

            st.dataframe(
                df_mostrar,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Mostrando {len(df_mostrar)} de {total} registros filtrados."
            )


# ===============================
# SIDEBAR INFO
# ===============================

st.sidebar.success(
    f"{st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button(
    "Cerrar sesión",
    key="btn_cerrar_sesion_configuracion"
):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")


# ===============================
# CIERRE DE CONEXIÓN
# ===============================

try:
    cursor.close()
    conn.close()
except Exception:
    pass