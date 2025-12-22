import streamlit as st
import pandas as pd
import plotly.express as px
from utils.conexionASupabase import get_connection

# ---------------------------------
# CONFIG
# ---------------------------------
st.set_page_config(page_title="Dashboard Farmacias", layout="wide")
st.title("📊 Dashboard de Ventas Farmacéuticas")

# ---------------------------------
# SEGURIDAD
# ---------------------------------
if "usuario" not in st.session_state:
    st.switch_page("login.py")

# ---------------------------------
# DATA
# ---------------------------------
conn = get_connection()

query = """
SELECT 
    v.venta_id,
    f.nombre AS farmacia,
    v.ventas_totales,
    v.tipo_registro,
    v.fecha
FROM ventas v
JOIN farmacias f ON v.farmacia_id = f.farmacia_id
ORDER BY v.fecha;
"""

df = pd.read_sql(query, conn)
conn.close()

df["fecha"] = pd.to_datetime(df["fecha"])

# ---------------------------------
# FILTROS
# ---------------------------------
st.sidebar.header("🔎 Filtros")

farmacias = ["Todas"] + sorted(df["farmacia"].dropna().unique())
farmacia_sel = st.sidebar.selectbox("Farmacia", farmacias)

anios = ["Todos"] + sorted(df["fecha"].dt.year.unique())
anio_sel = st.sidebar.selectbox("Año", anios)

meses = ["Todos"] + sorted(df["fecha"].dt.month.unique())
mes_sel = st.sidebar.selectbox("Mes", meses)

df_filt = df.copy()

if farmacia_sel != "Todas":
    df_filt = df_filt[df_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.year == anio_sel]

if mes_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.month == mes_sel]

# ---------------------------------
# KPI
# ---------------------------------
st.metric("💰 Ventas Totales", f"${df_filt['ventas_totales'].sum():,.2f}")

# ---------------------------------
# TENDENCIA
# ---------------------------------
st.subheader("📈 Tendencia de Ventas")

tipo = st.selectbox(
    "Visualización",
    ["Diaria", "Semanal", "Mensual"]
)

# ===== DIARIA =====
if tipo == "Diaria":
    df_trend = (
        df_filt.groupby(df_filt["fecha"].dt.date)["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["Etiqueta"] = pd.to_datetime(df_trend["fecha"]).dt.strftime("%A")
    df_trend["Orden"] = pd.to_datetime(df_trend["fecha"])

    fig = px.line(
        df_trend,
        x="Etiqueta",
        y="ventas_totales",
        markers=True,
        text="Etiqueta",
        title="Tendencia Diaria (por día de la semana)"
    )

# ===== SEMANAL =====
elif tipo == "Semanal":
    df_trend = (
        df_filt.groupby(df_filt["fecha"].dt.to_period("W"))["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["inicio"] = df_trend["fecha"].apply(lambda x: x.start_time)
    df_trend["fin"] = df_trend["fecha"].apply(lambda x: x.end_time)

    df_trend["Etiqueta"] = (
        "Semana " +
        df_trend["inicio"].dt.isocalendar().week.astype(str) +
        " (" +
        df_trend["inicio"].dt.strftime("%d %b") +
        " - " +
        df_trend["fin"].dt.strftime("%d %b") +
        ")"
    )

    fig = px.line(
        df_trend,
        x="Etiqueta",
        y="ventas_totales",
        markers=True,
        text="Etiqueta",
        title="Tendencia Semanal"
    )

# ===== MENSUAL =====
else:
    df_trend = (
        df_filt.groupby(df_filt["fecha"].dt.to_period("M"))["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["Etiqueta"] = df_trend["fecha"].dt.strftime("%B %Y")

    fig = px.line(
        df_trend,
        x="Etiqueta",
        y="ventas_totales",
        markers=True,
        text="Etiqueta",
        title="Tendencia Mensual"
    )

# ---------------------------------
# AJUSTES VISUALES IMPORTANTES
# ---------------------------------
fig.update_traces(
    textposition="top center",
    hovertemplate="<b>%{x}</b><br>Ventas: $%{y:,.2f}<extra></extra>"
)

fig.update_layout(
    xaxis_title="Periodo",
    yaxis_title="Ventas",
    uniformtext_minsize=10,
    uniformtext_mode="hide"
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------
# SESIÓN
# ---------------------------------
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("login.py")
