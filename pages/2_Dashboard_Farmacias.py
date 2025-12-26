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


st.set_page_config(page_title="Dashboard Farmacias", layout="wide")
st.title("📊 Dashboard de Ventas Farmacéuticas")

# ---------------------------------
# CARGA DE VENTAS
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
# CARGA DE GASTOS
# ---------------------------------
conn = get_connection()

query_gastos = """
SELECT
    g.gasto_id,
    f.nombre AS farmacia,
    g.monto,
    g.fecha,
    g.tipo_gasto,
    g.categoria
FROM gastos g
JOIN farmacias f ON g.farmacia_id = f.farmacia_id
ORDER BY g.fecha;
"""

df_gastos = pd.read_sql(query_gastos, conn)
conn.close()

df_gastos["fecha"] = pd.to_datetime(df_gastos["fecha"])




# ---------------------------------
# FILTROS DE VENTAS
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

#####
# FILTROS DE GASTOS
#####

df_gastos_filt = df_gastos.copy()

if farmacia_sel != "Todas":
    df_gastos_filt = df_gastos_filt[df_gastos_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.year == anio_sel]

if mes_sel != "Todos":
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.month == mes_sel]



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
# KPI FINANCIEROS
# ---------------------------------
ventas_totales = df_filt["ventas_totales"].sum()
gastos_totales = df_gastos_filt["monto"].sum()
ventas_netas = ventas_totales - gastos_totales

k1, k2, k3 = st.columns(3)

k1.metric("💰 Ventas Brutas", f"${ventas_totales:,.2f}")
k2.metric("💸 Gastos Totales", f"${gastos_totales:,.2f}")
k3.metric("💵 Ventas Netas", f"${ventas_netas:,.2f}")

if ventas_totales > 0:
    margen = (ventas_netas / ventas_totales) * 100
    st.caption(f"📊 Margen neto: **{margen:.2f}%**")

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

    df_trend["Etiqueta"] = (
        pd.to_datetime(df_trend["fecha"])
        .dt.strftime("%A")
        .map(DIAS_ES)
    )

    df_filt["semana"] = df_filt["fecha"].dt.isocalendar().week
    
    
    if not df_trend.empty:
        fecha_min = pd.to_datetime(df_trend["fecha"]).min()
        fecha_max = pd.to_datetime(df_trend["fecha"]).max()

        semana_num = fecha_min.isocalendar().week

        dia_inicio = DIAS_ES[fecha_min.strftime("%A")]
        dia_fin = DIAS_ES[fecha_max.strftime("%A")]

        mes_inicio = MESES_ES[fecha_min.strftime("%B")]
        mes_fin = MESES_ES[fecha_max.strftime("%B")]

        st.caption(
            f"📅 **Semana {semana_num}** — "
            f"{dia_inicio} {fecha_min.day} {mes_inicio} {fecha_min.year} "
            f"a "
            f"{dia_fin} {fecha_max.day} {mes_fin} {fecha_max.year}"
        )

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
    df_trend["inicio"].dt.strftime("%d") + " " +
    df_trend["inicio"].dt.strftime("%B").map(MESES_ES) +
    " - " +
    df_trend["fin"].dt.strftime("%d") + " " +
    df_trend["fin"].dt.strftime("%B").map(MESES_ES) +
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

fig.update_traces(
    textposition="top center"
)

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

st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)
if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("login.py")





