import streamlit as st
import bcrypt
import pandas as pd
from utils.conexionASupabase import get_connection

# ===============================
# SEGURIDAD
# ===============================
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

if st.session_state["usuario"]["rol"] != "admin":
    st.error("No tienes permisos para esta sección")
    st.stop()

st.set_page_config(page_title="Gestión de Usuarios", layout="wide")
st.title("👥 Gestión de Usuarios")

# ===============================
# TABS
# ===============================
tab_crear, tab_admin = st.tabs(["➕ Crear usuario", "🛠️ Administrar usuarios"])

# =====================================================
# ➕ CREAR USUARIO
# =====================================================
with tab_crear:
    st.subheader("➕ Crear nuevo usuario")

    nombre = st.text_input("Nombre completo")
    email = st.text_input("Correo")
    password = st.text_input("Contraseña", type="password")
    rol = st.selectbox("Rol", ["admin", "empleado"])

    if st.button("Crear usuario"):
        if not nombre or not email or not password:
            st.warning("Completa todos los campos")
            st.stop()

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO usuarios (nombre, email, password_hash, rol)
                VALUES (%s, %s, %s, %s)
            """, (nombre, email, password_hash, rol))
            conn.commit()
            st.success("✅ Usuario creado correctamente")
        except Exception as e:
            st.error(f"❌ Error: {e}")
        finally:
            cursor.close()
            conn.close()

# =====================================================
# 🛠️ ADMINISTRAR USUARIOS
# =====================================================
with tab_admin:
    st.subheader("🛠️ Administrar usuarios")

    conn = get_connection()
    df_users = pd.read_sql("""
        SELECT usuario_id, nombre, email, rol
        FROM usuarios
        ORDER BY nombre
    """, conn)
    conn.close()

    st.dataframe(df_users, use_container_width=True, hide_index=True)

    st.divider()

    usuario_sel = st.selectbox(
        "Selecciona un usuario",
        df_users["usuario_id"],
        format_func=lambda x: df_users[df_users["usuario_id"] == x]["nombre"].values[0]
    )

    user_data = df_users[df_users["usuario_id"] == usuario_sel].iloc[0]

    nuevo_nombre = st.text_input("Nombre", user_data["nombre"])
    nuevo_rol = st.selectbox("Rol", ["admin", "empleado"], index=0 if user_data["rol"] == "admin" else 1)

    cambiar_pass = st.checkbox("Cambiar contraseña")
    nueva_pass = None

    if cambiar_pass:
        nueva_pass = st.text_input("Nueva contraseña", type="password")

    col1, col2 = st.columns(2)

    # ===============================
    # MODIFICAR USUARIO
    # ===============================
    with col1:
        if st.button("💾 Guardar cambios"):
            conn = get_connection()
            cursor = conn.cursor()

            try:
                if cambiar_pass and nueva_pass:
                    password_hash = bcrypt.hashpw(nueva_pass.encode(), bcrypt.gensalt()).decode()
                    cursor.execute("""
                        UPDATE usuarios
                        SET nombre=%s, rol=%s, password_hash=%s
                        WHERE usuario_id=%s
                    """, (nuevo_nombre, nuevo_rol, password_hash, usuario_sel))
                else:
                    cursor.execute("""
                        UPDATE usuarios
                        SET nombre=%s, rol=%s
                        WHERE usuario_id=%s
                    """, (nuevo_nombre, nuevo_rol, usuario_sel))

                conn.commit()
                st.success("✅ Usuario actualizado")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error: {e}")
            finally:
                cursor.close()
                conn.close()

    # ===============================
    # ELIMINAR USUARIO
    # ===============================
    with col2:
        if usuario_sel == st.session_state["usuario"]["id"]:
            st.warning("⚠️ No puedes eliminar tu propio usuario")
        else:
            if st.button("🗑️ Eliminar usuario"):
                conn = get_connection()
                cursor = conn.cursor()

                try:
                    cursor.execute("""
                        DELETE FROM usuarios
                        WHERE usuario_id = %s
                    """, (usuario_sel,))
                    conn.commit()
                    st.success("🗑️ Usuario eliminado")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                finally:
                    cursor.close()
                    conn.close()

# ===============================
# SIDEBAR
# ===============================
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("login.py")
