import streamlit as st
import pandas as pd
import plotly.express as px
from utils.conexionASupabase import get_connection

# ---------------------------------
# TRADUCCIONES
# ---------------------------------
DIAS_ES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}

MESES_ES = {
    "January": "Enero",
    "February": "Febrero",
    "March": "Marzo",
    "April": "Abril",
    "May": "Mayo",
    "June": "Junio",
    "July": "Julio",
    "August": "Agosto",
    "September": "Septiembre",
    "October": "Octubre",
    "November": "Noviembre",
    "December": "Diciembre"
}

# ---------------------------------
# CONFIG
# ---------------------------------
st.set_page_config(page_title="Dashboard Farmacias", layout="wide")
st.title("📊 Dashboard de Ventas Farmacéuticas")

# ---------------------------------
# SEGURIDAD
# ---------------------------------
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

# ---------------------------------
# CARGA DE VENTAS
# ---------------------------------
conn = get_connection()

df = pd.read_sql("""
    SELECT v.venta_id, f.nombre AS farmacia,
           v.ventas_totales, v.tipo_registro, v.fecha
    FROM ventas v
    JOIN farmacias f ON v.farmacia_id = f.farmacia_id
    ORDER BY v.fecha
""", conn)

df_gastos = pd.read_sql("""
    SELECT g.gasto_id, f.nombre AS farmacia,
           g.monto, g.fecha
    FROM gastos g
    JOIN farmacias f ON g.farmacia_id = f.farmacia_id
    ORDER BY g.fecha
""", conn)

conn.close()

df["fecha"] = pd.to_datetime(df["fecha"])
df_gastos["fecha"] = pd.to_datetime(df_gastos["fecha"])

# ---------------------------------
# FILTROS
# ---------------------------------
st.sidebar.header("🔎 Filtros")

farmacia_sel = st.sidebar.selectbox(
    "Farmacia",
    ["Todas"] + sorted(df["farmacia"].unique())
)

anio_sel = st.sidebar.selectbox(
    "Año",
    ["Todos"] + sorted(df["fecha"].dt.year.unique())
)

mes_sel = st.sidebar.selectbox(
    "Mes",
    ["Todos"] + sorted(df["fecha"].dt.month.unique())
)

df_filt = df.copy()
df_gastos_filt = df_gastos.copy()

if farmacia_sel != "Todas":
    df_filt = df_filt[df_filt["farmacia"] == farmacia_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.year == anio_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.year == anio_sel]

if mes_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.month == mes_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.month == mes_sel]

# ---------------------------------
# KPIs FINANCIEROS
# ---------------------------------
ventas_brutas = df_filt["ventas_totales"].sum()
gastos_totales = df_gastos_filt["monto"].sum()
ventas_netas = ventas_brutas - gastos_totales

k1, k2, k3 = st.columns(3)
k1.metric("💰 Ventas Brutas", f"${ventas_brutas:,.2f}")
k2.metric("💸 Gastos Totales", f"${gastos_totales:,.2f}")
k3.metric("💵 Ventas Netas", f"${ventas_netas:,.2f}")

if ventas_brutas > 0:
    margen = ventas_netas / ventas_brutas * 100
    st.caption(f"📊 Margen neto: **{margen:.2f}%**")

# ---------------------------------
# UTILIDAD POR FARMACIA
# ---------------------------------
st.subheader("💵 Utilidad por Farmacia")

df_utilidad = (
    df_filt.groupby("farmacia")["ventas_totales"].sum()
    .reset_index()
    .merge(
        df_gastos_filt.groupby("farmacia")["monto"].sum().reset_index(),
        on="farmacia",
        how="left"
    )
)

df_utilidad["monto"] = df_utilidad["monto"].fillna(0)
df_utilidad["utilidad"] = df_utilidad["ventas_totales"] - df_utilidad["monto"]

fig_utilidad = px.bar(
    df_utilidad,
    x="farmacia",
    y="utilidad",
    title="Utilidad Neta por Farmacia"
)

st.plotly_chart(fig_utilidad, use_container_width=True)

# ---------------------------------
# TENDENCIAS
# ---------------------------------
st.subheader("📈 Tendencia de Ventas")

tipo = st.selectbox(
    "Visualización",
    ["Diaria", "Semanal", "Mensual"]
)

# ===== DIARIA (UNA SEMANA) =====
if tipo == "Diaria":

    df_filt["semana"] = df_filt["fecha"].dt.isocalendar().week
    semanas = sorted(df_filt["semana"].unique())

    semana_sel = st.selectbox("Semana", semanas)

    df_semana = df_filt[df_filt["semana"] == semana_sel]

    df_trend = (
        df_semana.groupby(df_semana["fecha"].dt.date)["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["Etiqueta"] = (
        pd.to_datetime(df_trend["fecha"])
        .dt.strftime("%A")
        .map(DIAS_ES)
    )

    fecha_min = df_semana["fecha"].min()
    fecha_max = df_semana["fecha"].max()

    st.caption(
        f"📅 Semana {semana_sel}: "
        f"{fecha_min.strftime('%d %B %Y')} a {fecha_max.strftime('%d %B %Y')}"
    )

    fig = px.line(
        df_trend,
        x="Etiqueta",
        y="ventas_totales",
        markers=True,
        text="Etiqueta",
        title="Tendencia Diaria"
    )

# ===== SEMANAL (DEL MES) =====
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
        df_trend["inicio"].dt.strftime("%d %B").map(MESES_ES) +
        " - " +
        df_trend["fin"].dt.strftime("%d %B").map(MESES_ES) +
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

    df_trend["Etiqueta"] = (
        df_trend["fecha"].dt.strftime("%B").map(MESES_ES)
        + " " +
        df_trend["fecha"].dt.strftime("%Y")
    )

    fig = px.line(
        df_trend,
        x="Etiqueta",
        y="ventas_totales",
        markers=True,
        text="Etiqueta",
        title="Tendencia Mensual"
    )

fig.update_traces(textposition="top center")
st.plotly_chart(fig, use_container_width=True)



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
# GASTOS POR FARMACIA
# ---------------------------------
st.subheader("💸 Gastos Totales por Farmacia")

df_gastos_farma = (
    df_gastos_filt.groupby("farmacia")["monto"]
    .sum()
    .reset_index()
    .sort_values("monto", ascending=False)
)

fig_gastos = px.bar(
    df_gastos_farma,
    x="farmacia",
    y="monto",
    title="Gastos Totales por Farmacia"
)

st.plotly_chart(fig_gastos, use_container_width=True)


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

# ---------------------------------
# SIDEBAR
# ---------------------------------
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("login.py")

