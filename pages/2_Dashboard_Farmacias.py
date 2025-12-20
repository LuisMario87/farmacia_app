import streamlit as st
import pandas as pd
import plotly.express as px
from utils.conexionASupabase import get_connection

st.set_page_config(page_title="Dashboard Farmacias", layout="wide")
st.title("📊 Dashboard de Ventas Farmacéuticas")

# ---------------------------------
# CARGA DE DATOS
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

# Asegurar tipo fecha
df["fecha"] = pd.to_datetime(df["fecha"])

# ---------------------------------
# FILTROS
# ---------------------------------
st.sidebar.header("🔎 Filtros")

farmacias = ["Todas"] + sorted(df["farmacia"].unique().tolist())
farmacia_sel = st.sidebar.selectbox("Farmacia", farmacias)

anios = ["Todos"] + sorted(df["fecha"].dt.year.unique().tolist())
anio_sel = st.sidebar.selectbox("Año", anios)

meses = ["Todos"] + sorted(df["fecha"].dt.month.unique().tolist())
mes_sel = st.sidebar.selectbox("Mes", meses)

df_filt = df.copy()

if farmacia_sel != "Todas":
    df_filt = df_filt[df_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.year == anio_sel]

if mes_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.month == mes_sel]

# ---------------------------------
# KPI GENERAL
# ---------------------------------
ventas_totales = df_filt["ventas_totales"].sum()
st.metric("💰 Ventas Totales", f"${ventas_totales:,.2f}")

# ---------------------------------
# PROMEDIOS
# ---------------------------------
st.subheader("📌 Promedios de Venta")

# Diario
ventas_diarias = df_filt[df_filt["tipo_registro"] == "diario"]
promedio_diario = (
    ventas_diarias
    .groupby(ventas_diarias["fecha"].dt.date)["ventas_totales"]
    .sum()
    .mean()
)

# Semanal
ventas_semanales = df_filt[df_filt["tipo_registro"] == "semanal"]
promedio_semanal = (
    ventas_semanales
    .groupby(ventas_semanales["fecha"].dt.to_period("W"))["ventas_totales"]
    .sum()
    .mean()
)

# Mensual
ventas_mensuales = df_filt[df_filt["tipo_registro"] == "mensual"]
promedio_mensual = (
    ventas_mensuales
    .groupby(ventas_mensuales["fecha"].dt.to_period("M"))["ventas_totales"]
    .sum()
    .mean()
)

c1, c2, c3 = st.columns(3)

c1.metric("📅 Promedio Diario", f"${0 if pd.isna(promedio_diario) else promedio_diario:,.2f}")
c2.metric("🗓 Promedio Semanal", f"${0 if pd.isna(promedio_semanal) else promedio_semanal:,.2f}")
c3.metric("📆 Promedio Mensual", f"${0 if pd.isna(promedio_mensual) else promedio_mensual:,.2f}")

# ---------------------------------
# TENDENCIA DIARIA
# ---------------------------------
if not ventas_diarias.empty:
    st.subheader("📉 Tendencia Diaria de Ventas")

    df_daily = (
        ventas_diarias
        .groupby(ventas_diarias["fecha"].dt.date)["ventas_totales"]
        .sum()
        .reset_index()
        .rename(columns={"fecha": "Fecha"})
    )

    fig_daily = px.line(
        df_daily,
        x="Fecha",
        y="ventas_totales",
        markers=True,
        title="Tendencia diaria de ventas"
    )

    st.plotly_chart(fig_daily, use_container_width=True)

# ---------------------------------
# COMPARACIÓN ENTRE FARMACIAS
# ---------------------------------
st.subheader("🏪 Ventas Totales por Farmacia")

df_farma = (
    df_filt.groupby("farmacia")["ventas_totales"]
    .sum()
    .reset_index()
    .sort_values("ventas_totales", ascending=False)
)

fig_farma = px.bar(
    df_farma,
    x="farmacia",
    y="ventas_totales",
    title="Ventas Totales por Farmacia"
)

st.plotly_chart(fig_farma, use_container_width=True)

# ---------------------------------
# TOP FARMACIA DEL MES
# ---------------------------------
st.subheader("🥇 Top Farmacia del Periodo")

if not df_filt.empty:
    top = (
        df_filt.groupby("farmacia")["ventas_totales"]
        .sum()
        .reset_index()
        .sort_values("ventas_totales", ascending=False)
        .head(1)
    )

    st.success(
        f"🥇 {top.iloc[0]['farmacia']} — "
        f"${top.iloc[0]['ventas_totales']:,.2f}"
    )
else:
    st.info("No hay datos para los filtros seleccionados")
