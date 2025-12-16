import streamlit as st
import pandas as pd
import plotly.express as px
from utils.conexionASupabase import get_connection

st.title("📊 Dashboard de Ventas Farmacéuticas")

conn = get_connection()

query = """
SELECT v.venta_id, f.nombre AS farmacia,
       v.ventas_totales, v.tipo_registro,
       v.dia, v.semana, v.mes, v.anio
FROM ventas v
JOIN farmacias f ON v.farmacia_id = f.farmacia_id
ORDER BY anio, mes, semana, dia;
"""

df = pd.read_sql(query, conn)
conn.close()

# -------------------------------
# FILTROS
# -------------------------------
farmacias = ["Todas"] + sorted(df["farmacia"].unique().tolist())
farmacia_sel = st.selectbox("Farmacia", farmacias)

anios = ["Todos"] + sorted(df["anio"].unique().tolist())
anio_sel = st.selectbox("Año", anios)

meses = ["Todos"] + sorted(df["mes"].unique().tolist())
mes_sel = st.selectbox("Mes", meses)

df_filt = df.copy()

if farmacia_sel != "Todas":
    df_filt = df_filt[df_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["anio"] == anio_sel]

if mes_sel != "Todos":
    df_filt = df_filt[df_filt["mes"] == mes_sel]

# -------------------------------
# KPIs GENERALES
# -------------------------------
ventas_totales = df_filt["ventas_totales"].sum()

st.metric("💰 Ventas Totales", f"${ventas_totales:,.2f}")

# -------------------------------
# PROMEDIOS
# -------------------------------
st.subheader("📌 Promedios")

# Diario
ventas_diarias = df_filt[df_filt["tipo_registro"] == "diario"]
promedio_diario = (
    ventas_diarias.groupby(["anio", "mes", "dia"])["ventas_totales"]
    .sum()
    .mean()
)

# Semanal
ventas_semanales = df_filt[df_filt["tipo_registro"] == "semanal"]
promedio_semanal = (
    ventas_semanales.groupby(["anio", "mes", "semana"])["ventas_totales"]
    .sum()
    .mean()
)

# Mensual
ventas_mensuales = df_filt[df_filt["tipo_registro"] == "mensual"]
promedio_mensual = (
    ventas_mensuales.groupby(["anio", "mes"])["ventas_totales"]
    .sum()
    .mean()
)

c1, c2, c3 = st.columns(3)

c1.metric("📅 Promedio Diario", f"${promedio_diario:,.2f}")
c2.metric("🗓 Promedio Semanal", f"${promedio_semanal:,.2f}")
c3.metric("📆 Promedio Mensual", f"${promedio_mensual:,.2f}")

# -------------------------------
# TENDENCIA DIARIA
# -------------------------------
if not ventas_diarias.empty:
    st.subheader("📉 Tendencia Diaria")

    df_daily = (
        ventas_diarias
        .groupby(["anio", "mes", "dia"])["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_daily["fecha"] = pd.to_datetime(
        dict(
            year=df_daily["anio"],
            month=df_daily["mes"],
            day=df_daily["dia"]
        )
    )

    fig_daily = px.line(
        df_daily,
        x="fecha",
        y="ventas_totales",
        title="Tendencia diaria de ventas",
        markers=True
    )

    st.plotly_chart(fig_daily, use_container_width=True)

# -------------------------------
# COMPARACIÓN ENTRE FARMACIAS
# -------------------------------
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

# -------------------------------
# TOP FARMACIA DEL MES
# -------------------------------
st.subheader("🥇 Top Farmacia del Mes")

if mes_sel != "Todos" and anio_sel != "Todos":
    df_mes = df_filt.copy()

    top = (
        df_mes.groupby("farmacia")["ventas_totales"]
        .sum()
        .reset_index()
        .sort_values("ventas_totales", ascending=False)
        .head(1)
    )

    if not top.empty:
        st.success(
            f"🥇 {top.iloc[0]['farmacia']} — "
            f"${top.iloc[0]['ventas_totales']:,.2f}"
        )
else:
    st.info("Selecciona año y mes para ver la farmacia ganadora")
