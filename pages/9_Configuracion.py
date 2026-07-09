import streamlit as st
import pandas as pd

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

roles_permitidos = ["admin"]

if rol_usuario not in roles_permitidos:
    st.error("No tienes permisos para esta sección")
    st.stop()


# ===============================
# CONEXIÓN
# ===============================

conn = get_connection()
cursor = conn.cursor()


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

    st.info("Aquí integraremos la lógica de la página de Gestión de usuarios.")


# ==================================================
# TAB 2 - GESTIÓN DE FARMACIAS
# ==================================================

with tab2:

    st.subheader("Gestión de farmacias")

    st.info("Aquí integraremos la lógica de la página de Gestión de farmacias.")


# ==================================================
# TAB 3 - LOGS
# ==================================================

with tab3:

    st.subheader("Logs del sistema")

    st.info("Aquí integraremos la lógica de la página de Logs.")


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