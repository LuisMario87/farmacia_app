import streamlit as st
import pandas as pd
import plotly.express as px
from utils.conexionASupabase import get_connection

# --------------------------------------------------
# CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(page_title="Dashboard Farmacias", layout="wide")
st.title("📊 Dashboard de Ventas Farmacéuticas")

# --------------------------------------------------
# CARGA DE DATOS
# --------------------------------------------------
conn = get_connection()

query = """
SELECT
    v.venta_id,
    f.nombre AS farmacia,
    f.ciudad,
    v.ventas_totales,
    v.tipo_registro,
    v.fecha
FROM ventas v
JOIN farmacias f ON v.farmacia_id = f.farmacia_id
ORDER BY v.fecha;
"""

df = pd.read_sql(query, conn)
conn.close()

# Convertir fecha
df["fecha"] = pd.to_datetime(df["fecha"])

# Columnas auxiliares (NO BD)
df["anio"] = df["fecha"].dt.year
df["mes"] = df["fecha"].dt.month
df["semana"] = df["fecha"].dt.isocalendar().week
df["dia_semana"] = df["fecha"].dt.day_name(locale="es_ES")
df["fecha_legible"] = df["fecha"].dt.strftime("%d %B %Y")

# --------------------------------------------------
# FILTROS
# --------------------------------------------------
st.subheader("🎛️ Filtros")

c1, c2, c3 = st.columns(3)

with c1:
    ciudad_sel = st.selectbox(
        "Ciudad",
        ["Todas"] + sorted(df["ciudad"].unique())
    )

with c2:
    farmacia_sel = st.selectbox(
        "Farmacia",
        ["Todas"] + sorted(df["farmacia"].unique())
    )

with c3:
    anio_sel = st.selectbox(
        "Año",
        ["Todos"] + sorted(df["anio"].unique())
    )

df_filt = df.copy()

if ciudad_sel != "Todas":
    df_filt = df_filt[df_filt["ciudad"] == ciudad_sel]

if farmacia_sel != "Todas":
    df_filt = df_filt[df_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["anio"] == anio_sel]

# --------------------------------------------------
# KPIs
# --------------------------------------------------
st.divider()
st.subheader("📌 KPIs Generales")

ventas_totales = df_filt["ventas_totales"].sum()
promedio_registro = df_filt["ventas_totales"].mean()

k1, k2 = st.columns(2)

k1.metric("💰 Ventas Totales", f"${ventas_totales:,.2f}")
k2.metric("📊 Promedio por Registro", f"${promedio_registro:,.2f}")

# --------------------------------------------------
# SELECTOR DE TENDENCIA
# --------------------------------------------------
st.divider()
st.subheader("📈 Tendencia de Ventas")

tipo_vista = st.radio(
    "Ver tendencia:",
    ["Diaria", "Semanal", "Mensual"],
    horizontal=True
)

# --------------------------------------------------
# TENDENCIA DIARIA
# --------------------------------------------------
if tipo_vista == "Diaria":

    df_daily = (
        df_filt[df_filt["tipo_registro"] == "diario"]
        .groupby("fecha", as_index=False)["ventas_totales"]
        .sum()
    )

    if df_daily.empty:
        st.info("No hay registros diarios para los filtros seleccionados.")
    else:
        df_daily["dia_semana"] = df_daily["fecha"].dt.day_name(locale="es_ES")
        df_daily["fecha_legible"] = df_daily["fecha"].dt.strftime("%d %B %Y")

        fig = px.line(
            df_daily,
            x="fecha",
            y="ventas_totales",
            markers=True,
            title="📅 Tendencia Diaria de Ventas"
        )

        fig.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "📆 %{customdata[1]}<br>"
                "💰 $%{y:,.2f}<extra></extra>"
            ),
            customdata=df_daily[["dia_semana", "fecha_legible"]]
        )

        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TENDENCIA SEMANAL
# --------------------------------------------------
elif tipo_vista == "Semanal":

    df_weekly = (
        df_filt[df_filt["tipo_registro"] == "semanal"]
        .groupby(["anio", "semana"], as_index=False)["ventas_totales"]
        .sum()
    )

    if df_weekly.empty:
        st.info("No hay registros semanales para los filtros seleccionados.")
    else:
        df_weekly["etiqueta"] = (
            "Semana " + df_weekly["semana"].astype(str)
            + " / " + df_weekly["anio"].astype(str)
        )

        fig = px.line(
            df_weekly,
            x="etiqueta",
            y="ventas_totales",
            markers=True,
            title="🗓️ Tendencia Semanal de Ventas"
        )

        fig.update_traces(
            hovertemplate=(
                "<b>%{x}</b><br>"
                "💰 $%{y:,.2f}<extra></extra>"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# TENDENCIA MENSUAL
# --------------------------------------------------
else:

    df_monthly = (
        df_filt[df_filt["tipo_registro"] == "mensual"]
        .groupby(["anio", "mes"], as_index=False)["ventas_totales"]
        .sum()
    )

    if df_monthly.empty:
        st.info("No hay registros mensuales para los filtros seleccionados.")
    else:
        df_monthly["mes_legible"] = pd.to_datetime(
            dict(
                year=df_monthly["anio"],
                month=df_monthly["mes"],
                day=1
            )
        ).dt.strftime("%B %Y").str.capitalize()

        fig = px.line(
            df_monthly,
            x="mes_legible",
            y="ventas_totales",
            markers=True,
            title="📆 Tendencia Mensual de Ventas"
        )

        fig.update_traces(
            hovertemplate=(
                "<b>%{x}</b><br>"
                "💰 $%{y:,.2f}<extra></extra>"
            )
        )

        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# COMPARACIÓN ENTRE FARMACIAS
# --------------------------------------------------
st.divider()
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
