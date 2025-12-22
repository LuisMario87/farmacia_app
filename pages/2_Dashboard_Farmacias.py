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




# Bloquear acceso si no hay sesión
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

df = pd.read_sql(query, conn)
conn.close()

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
# PERIODO ANALIZADO (KPIs)
# ---------------------------------
if anio_sel == "Todos":
    periodo_kpi = "Todos los años"
elif mes_sel == "Todos":
    periodo_kpi = f"Año {anio_sel}"
else:
    nombre_mes = pd.to_datetime(f"{anio_sel}-{mes_sel}-01").strftime("%B")
    periodo_kpi = f"{nombre_mes.capitalize()} {anio_sel}"

st.caption(f"📅 **Periodo analizado:** {periodo_kpi}")


# ---------------------------------
# KPI GENERAL
# ---------------------------------
ventas_totales = df_filt["ventas_totales"].sum()
st.metric("💰 Ventas Totales", f"${ventas_totales:,.2f}")

# ---------------------------------
# PROMEDIOS
# ---------------------------------
st.subheader("📌 Promedios")

ventas_diarias = df_filt[df_filt["tipo_registro"] == "diario"]
ventas_semanales = df_filt[df_filt["tipo_registro"] == "semanal"]
ventas_mensuales = df_filt[df_filt["tipo_registro"] == "mensual"]

prom_diario = (
    ventas_diarias.groupby(ventas_diarias["fecha"].dt.date)["ventas_totales"]
    .sum()
    .mean()
)

prom_semanal = (
    ventas_semanales.groupby(ventas_semanales["fecha"].dt.to_period("W"))["ventas_totales"]
    .sum()
    .mean()
)

prom_mensual = (
    ventas_mensuales.groupby(ventas_mensuales["fecha"].dt.to_period("M"))["ventas_totales"]
    .sum()
    .mean()
)

c1, c2, c3 = st.columns(3)

c1.metric("📅 Promedio Diario", f"${0 if pd.isna(prom_diario) else prom_diario:,.2f}")
c2.metric("🗓 Promedio Semanal", f"${0 if pd.isna(prom_semanal) else prom_semanal:,.2f}")
c3.metric("📆 Promedio Mensual", f"${0 if pd.isna(prom_mensual) else prom_mensual:,.2f}")

# ---------------------------------
# TENDENCIA (DINÁMICA)
# ---------------------------------
st.subheader("📈 Tendencia de Ventas")

tipo_tendencia = st.selectbox(
    "Selecciona la granularidad",
    ["Diaria", "Semanal", "Mensual"]
)

if tipo_tendencia == "Diaria":
    df_trend = (
        df_filt.groupby(df_filt["fecha"].dt.date)["ventas_totales"]
        .sum()
        .reset_index()
        .rename(columns={"fecha": "Fecha"})
    )
    titulo = "Tendencia Diaria de Ventas"

elif tipo_tendencia == "Semanal":
    df_trend = (
        df_filt
        .groupby(df_filt["fecha"].dt.to_period("W"))["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["inicio_semana"] = df_trend["fecha"].apply(lambda x: x.start_time)
    df_trend["fin_semana"] = df_trend["fecha"].apply(lambda x: x.end_time)

    rango_inicio = df_trend["inicio_semana"].min()
    rango_fin = df_trend["fin_semana"].max()

    rango_texto = (
        f"{rango_inicio.strftime('%A %d %B')} – "
        f"{rango_fin.strftime('%A %d %B %Y')}"
    )

    st.caption(f"📅 **Periodo visualizado:** {rango_texto}")

    df_trend["Fecha"] = df_trend["inicio_semana"]
    titulo = "Tendencia Semanal de Ventas"


else:  # Mensual
    df_trend = (
        df_filt
        .groupby(df_filt["fecha"].dt.to_period("M"))["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["mes_inicio"] = df_trend["fecha"].dt.to_timestamp()

    mes_inicio = df_trend["mes_inicio"].min()
    mes_fin = df_trend["mes_inicio"].max()

    if mes_inicio == mes_fin:
        rango_texto = mes_inicio.strftime("%B %Y")
    else:
        rango_texto = (
            f"{mes_inicio.strftime('%B %Y')} – "
            f"{mes_fin.strftime('%B %Y')}"
        )

    st.caption(f"📅 **Periodo visualizado:** {rango_texto}")

    df_trend["Fecha"] = df_trend["mes_inicio"]
    titulo = "Tendencia Mensual de Ventas"
####Modificacion mensual arriba

fig_trend = px.line(
    df_trend,
    x="Fecha",
    y="ventas_totales",
    markers=True,
    title=titulo
)

st.plotly_chart(fig_trend, use_container_width=True)

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
# TOP FARMACIA
# ---------------------------------
st.subheader("🥇 Farmacia con Mayor Venta")

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

st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)
if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("login.py")






