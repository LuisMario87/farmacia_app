import streamlit as st
import bcrypt
from utils.conexionASupabase import get_connection

st.set_page_config(
    page_title="Sistema Farmacias",
    layout="centered",
    initial_sidebar_state="collapsed"  # 👈 IMPORTANTE
)
# Ocultar sidebar si no hay sesión
if "usuario" not in st.session_state:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] { display: none; }
        </style>
        """,
        unsafe_allow_html=True
    )
# Si YA hay sesión, redirigir
if "usuario" in st.session_state:
    st.switch_page("pages/2_Dashboard.py")

st.title("🔐 Sistema de Ventas Farmacéuticas")

email = st.text_input("Correo")
password = st.text_input("Contraseña", type="password")

if st.button("Ingresar"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT usuario_id, nombre, password_hash, rol
        FROM usuarios
        WHERE email = %s AND activo = TRUE
    """, (email,))

    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        if bcrypt.checkpw(password.encode(), user[2].encode()):
            st.session_state["usuario"] = {
                "id": user[0],
                "nombre": user[1],
                "rol": user[3]
            }
            st.success(f"Bienvenido {user[1]}")
            st.rerun()
        else:
            st.error("❌ Contraseña incorrecta")
    else:
        st.error("❌ Usuario no encontrado")


