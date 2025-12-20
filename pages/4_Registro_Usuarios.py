import streamlit as st
import bcrypt
from utils.conexionASupabase import get_connection

# Bloquear acceso si no hay sesión
if "usuario" not in st.session_state:
    st.switch_page("login.py")
st.title("👥 Gestión de Usuarios")

# 🔒 Control de acceso
if "usuario" not in st.session_state:
    st.warning("Debes iniciar sesión")
    st.stop()

if st.session_state["usuario"]["rol"] != "admin":
    st.error("No tienes permisos para esta sección")
    st.stop()

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
        st.success("Usuario creado correctamente")
    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        cursor.close()
        conn.close()
