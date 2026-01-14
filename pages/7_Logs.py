import streamlit as st
import pandas as pd
from utils.conexionASupabase import get_connection

# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="Logs del Sistema", layout="wide")
st.title("📜 Historial de Movimientos (Logs)")

# ===============================
# SEGURIDAD
# ===============================
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

if st.session_state["usuario"]["rol"] != "admin":
    st.error("No tienes permisos para esta sección")
    st.stop()

# ===============================
# CARGA DE DATOS
# ===============================
conn = get_connection()

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

conn.close()

df_logs["fecha"] = pd.to_datetime(df_logs["fecha"])

# ===============================
# FILTROS
# ===============================
st.sidebar.header("🔎 Filtros")

usuarios = ["Todos"] + sorted(df_logs["usuario_nombre"].dropna().unique())
usuario_sel = st.sidebar.selectbox("Usuario", usuarios)

acciones = ["Todas"] + sorted(df_logs["accion"].dropna().unique())
accion_sel = st.sidebar.selectbox("Acción", acciones)

anios = ["Todos"] + sorted(df_logs["fecha"].dt.year.unique())
anio_sel = st.sidebar.selectbox("Año", anios)

meses = ["Todos"] + sorted(df_logs["fecha"].dt.month.unique())
mes_sel = st.sidebar.selectbox("Mes", meses)

# ===============================
# APLICAR FILTROS
# ===============================
df_filt = df_logs.copy()

if usuario_sel != "Todos":
    df_filt = df_filt[df_filt["usuario_nombre"] == usuario_sel]

if accion_sel != "Todas":
    df_filt = df_filt[df_filt["accion"] == accion_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.year == anio_sel]

if mes_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.month == mes_sel]

# ===============================
# TABLA DE LOGS
# ===============================
st.subheader("📋 Registros de actividad")

col1, col2 = st.columns([2, 1])

with col1:
    busqueda = st.text_input("🔍 Buscar en descripción")

with col2:
    page_size = st.selectbox("Filas por página", [10, 25, 50], key="logs_ps")

if busqueda:
    df_filt = df_filt[
        df_filt["descripcion"].str.contains(busqueda, case=False, na=False)
    ]

total = len(df_filt)
total_pages = max(1, (total - 1) // page_size + 1)

page = st.number_input(
    "Página",
    1,
    total_pages,
    1,
    key="logs_page"
)

start = (page - 1) * page_size
end = start + page_size

st.dataframe(
    df_filt.iloc[start:end],
    use_container_width=True,
    hide_index=True
)

st.caption(f"Página {page} de {total_pages}")

# ===============================
# INFO RESUMEN
# ===============================
st.divider()

st.subheader("📊 Resumen rápido")

c1, c2, c3 = st.columns(3)

c1.metric("Total de logs", len(df_logs))
c2.metric("Usuarios únicos", df_logs["usuario_nombre"].nunique())
c3.metric("Acciones distintas", df_logs["accion"].nunique())

# ===============================
# SIDEBAR INFO
# ===============================
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")
