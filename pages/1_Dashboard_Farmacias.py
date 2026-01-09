import streamlit as st
import pandas as pd
import plotly.express as px
from utils.conexionASupabase import get_connection
from reports.reporte_financiero import generar_reporte_financiero

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
    "December": "Diciembre",
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ---------------------------------
# CONFIG
# ---------------------------------
st.set_page_config(page_title="Dashboard", layout="wide")
st.title("📊 Dashboard Financiero")

# ---------------------------------
# SEGURIDAD
# ---------------------------------
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

if st.session_state["usuario"]["rol"] != "admin":
    st.error("No tienes permisos para esta sección")
    st.stop()

# ---------------------------------
# CARGA DE DATOS
# ---------------------------------
conn = get_connection()

df = pd.read_sql("""
SELECT 
    v.venta_id,
    f.nombre AS farmacia,
    v.ventas_totales,
    v.tipo_registro,
    v.fecha
FROM ventas v
JOIN farmacias f ON v.farmacia_id = f.farmacia_id
ORDER BY v.fecha;
""", conn)

df_gastos = pd.read_sql("""
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
""", conn)

conn.close()

df["fecha"] = pd.to_datetime(df["fecha"])
df_gastos["fecha"] = pd.to_datetime(df_gastos["fecha"])

# ---------------------------------
# FILTROS
# ---------------------------------
st.sidebar.header("🔎 Filtros")

farmacias = ["Todas"] + sorted(df["farmacia"].unique())
farmacia_sel = st.sidebar.selectbox("Farmacia", farmacias)

anios = ["Todos"] + sorted(df["fecha"].dt.year.unique())
anio_sel = st.sidebar.selectbox("Año", anios)

meses = ["Todos"] + [
    f"{m} - {MESES_ES[m]}" for m in sorted(df["fecha"].dt.month.unique())
]
mes_sel = st.sidebar.selectbox("Mes", meses)

# ---------------------------------
# FILTRADO
# ---------------------------------
df_filt = df.copy()
df_gastos_filt = df_gastos.copy()

if farmacia_sel != "Todas":
    df_filt = df_filt[df_filt["farmacia"] == farmacia_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.year == anio_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.year == anio_sel]

mes_num = None
if mes_sel != "Todos":
    mes_num = int(mes_sel.split(" - ")[0])
    df_filt = df_filt[df_filt["fecha"].dt.month == mes_num]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.month == mes_num]

# ---------------------------------
# PERIODO ANALIZADO (VISIBLE)
# ---------------------------------
if anio_sel == "Todos":
    periodo_kpi = "Todos los años"
elif mes_sel == "Todos":
    periodo_kpi = f"Año {anio_sel}"
else:
    periodo_kpi = f"{MESES_ES[mes_num]} {anio_sel}"

if farmacia_sel != "Todas":
    periodo_kpi = f"{farmacia_sel} — {periodo_kpi}"

st.caption(f"📅 **Periodo analizado:** {periodo_kpi}")

# ---------------------------------
# 1️⃣ ESTADO DE RESULTADOS
# ---------------------------------
st.subheader("🧾 Estado de Resultados")

ventas_total = df_filt["ventas_totales"].sum()
gastos_total = df_gastos_filt["monto"].sum()
utilidad = ventas_total - gastos_total
margen = (utilidad / ventas_total * 100) if ventas_total > 0 else 0

c1, c2, c3 = st.columns(3)

c1.metric("Ventas Totales", f"${ventas_total:,.2f}")
c2.metric("Gastos Totales", f"${gastos_total:,.2f}")
c3.metric("Utilidad Operativa", f"${utilidad:,.2f}")

st.caption(f"📈 Margen de utilidad: **{margen:.2f}%**")

st.divider()

# ===============================
# COMPARATIVO VS PERIODO ANTERIOR
# ===============================

mes_num = None
if mes_sel != "Todos":
    mes_num = int(mes_sel.split(" - ")[0])

mostrar_comparativo = (
    anio_sel != "Todos" and
    mes_num is not None
)

if mostrar_comparativo:

    ventas_actual = df_filt["ventas_totales"].sum()
    gastos_actual = df_gastos_filt["monto"].sum()
    utilidad_actual = ventas_actual - gastos_actual

    mes_anterior = mes_num - 1
    anio_anterior = anio_sel

    if mes_anterior == 0:
        mes_anterior = 12
        anio_anterior -= 1

    df_ventas_ant = df[
        (df["fecha"].dt.year == anio_anterior) &
        (df["fecha"].dt.month == mes_anterior)
    ]

    df_gastos_ant = df_gastos[
        (df_gastos["fecha"].dt.year == anio_anterior) &
        (df_gastos["fecha"].dt.month == mes_anterior)
    ]

    if farmacia_sel != "Todas":
        df_ventas_ant = df_ventas_ant[df_ventas_ant["farmacia"] == farmacia_sel]
        df_gastos_ant = df_gastos_ant[df_gastos_ant["farmacia"] == farmacia_sel]

    ventas_ant = df_ventas_ant["ventas_totales"].sum()
    gastos_ant = df_gastos_ant["monto"].sum()
    utilidad_ant = ventas_ant - gastos_ant

    def variacion(actual, anterior):
        if anterior == 0:
            return 0, 0
        diff = actual - anterior
        pct = (diff / anterior) * 100
        return diff, pct

    v_diff, v_pct = variacion(ventas_actual, ventas_ant)
    g_diff, g_pct = variacion(gastos_actual, gastos_ant)
    u_diff, u_pct = variacion(utilidad_actual, utilidad_ant)

    st.subheader("📊 Comparativo vs periodo anterior")

    c1, c2, c3 = st.columns(3)

    c1.metric("Ventas", f"${ventas_actual:,.2f}", f"{v_diff:+,.2f} ({v_pct:+.1f}%)")
    c2.metric("Gastos", f"${gastos_actual:,.2f}", f"{g_diff:+,.2f} ({g_pct:+.1f}%)")
    c3.metric("Utilidad", f"${utilidad_actual:,.2f}", f"{u_diff:+,.2f} ({u_pct:+.1f}%)")

else:
    st.info("ℹ️ Selecciona un mes y año específico para ver la comparativa.")


# ---------------------------------
# 2️⃣ UTILIDAD POR FARMACIA
# ---------------------------------
st.subheader("💵 Utilidad por Farmacia")

df_utilidad = (
    df_filt.groupby("farmacia")["ventas_totales"].sum().reset_index()
    .merge(
        df_gastos_filt.groupby("farmacia")["monto"].sum().reset_index(),
        on="farmacia",
        how="left"
    )
)

df_utilidad["monto"] = df_utilidad["monto"].fillna(0)
df_utilidad["utilidad"] = df_utilidad["ventas_totales"] - df_utilidad["monto"]

fig_util = px.bar(
    df_utilidad,
    x="farmacia",
    y="utilidad",
    title="Utilidad Neta por Farmacia"
)

st.plotly_chart(fig_util, use_container_width=True)

st.divider()


# ---------------------------------
# 3️⃣ TENDENCIAS
# ---------------------------------
st.subheader("📈 Tendencia de Ventas")

tipo = st.selectbox("Visualización", ["Diaria", "Semanal", "Mensual"])

# ===== DIARIA (1 SEMANA) =====
if tipo == "Diaria":
    df_filt["semana_mes"] = ((df_filt["fecha"].dt.day - 1) // 7) + 1
    semana_sel = st.selectbox("Semana del mes", sorted(df_filt["semana_mes"].unique()))

    df_semana = df_filt[df_filt["semana_mes"] == semana_sel]

        # 🔹 Calcular rango real de fechas de la semana seleccionada
    fecha_inicio = df_semana["fecha"].min()
    fecha_fin = df_semana["fecha"].max()

    # 🔹 Obtener nombres de día en español
    dia_inicio = DIAS_ES[fecha_inicio.strftime("%A")]
    dia_fin = DIAS_ES[fecha_fin.strftime("%A")]

    mes_nombre = MESES_ES[fecha_inicio.month]

    st.caption(
        f"📅 **Periodo analizado:** "
        f"{dia_inicio} {fecha_inicio.day} de {mes_nombre} de {fecha_inicio.year} "
        f"a "
        f"{dia_fin} {fecha_fin.day} de {mes_nombre} de {fecha_fin.year}"
    )


    df_trend = (
        df_semana.groupby(df_semana["fecha"].dt.date)["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["Etiqueta"] = (
        pd.to_datetime(df_trend["fecha"]).dt.strftime("%A").map(DIAS_ES)
    )

    fig = px.line(
        df_trend,
        x="Etiqueta",
        y="ventas_totales",
        markers=True,
        title="Tendencia Diaria (una semana)"
    )

# ===== SEMANAL =====
elif tipo == "Semanal":

    df_trend = (
        df_filt.groupby(df_filt["fecha"].dt.to_period("W"))["ventas_totales"]
        .sum()
        .reset_index()
    )

    df_trend["inicio"] = df_trend["fecha"].apply(lambda x: x.start_time)
    df_trend["Etiqueta"] = "Semana " + df_trend["inicio"].dt.isocalendar().week.astype(str)

    fig = px.line(
        df_trend,
        x="Etiqueta",
        y="ventas_totales",
        markers=True,
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
        title="Tendencia Mensual"
    )

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------
# 4️⃣ PROMEDIOS (BASADOS EN VENTAS DIARIAS)
# ---------------------------------
st.subheader("📌 Promedios")

# Usamos SOLO ventas diarias como base real
ventas_diarias = df_filt.copy()

# 🔹 Promedio Diario
prom_diario = (
    ventas_diarias
    .groupby(ventas_diarias["fecha"].dt.date)["ventas_totales"]
    .sum()
    .mean()
)

# 🔹 Promedio Semanal (derivado de ventas diarias)
prom_semanal = (
    ventas_diarias
    .groupby(ventas_diarias["fecha"].dt.to_period("W"))["ventas_totales"]
    .sum()
    .mean()
)

# 🔹 Promedio Mensual (derivado de ventas diarias)
prom_mensual = (
    ventas_diarias
    .groupby(ventas_diarias["fecha"].dt.to_period("M"))["ventas_totales"]
    .sum()
    .mean()
)

c1, c2, c3 = st.columns(3)

c1.metric(
    "📅 Promedio Diario",
    f"${0 if pd.isna(prom_diario) else prom_diario:,.2f}"
)

c2.metric(
    "🗓 Promedio Semanal",
    f"${0 if pd.isna(prom_semanal) else prom_semanal:,.2f}"
)

c3.metric(
    "📆 Promedio Mensual",
    f"${0 if pd.isna(prom_mensual) else prom_mensual:,.2f}"
)

st.divider()


# ---------------------------------
# 5️⃣ COMPARATIVOS
# ---------------------------------
st.subheader("🏪 Ventas y Gastos por Farmacia")

df_farma = df_filt.groupby("farmacia")["ventas_totales"].sum().reset_index()
df_gasto_farma = df_gastos_filt.groupby("farmacia")["monto"].sum().reset_index()

st.plotly_chart(px.bar(df_farma, x="farmacia", y="ventas_totales", title="Ventas por Farmacia"), use_container_width=True)
st.plotly_chart(px.bar(df_gasto_farma, x="farmacia", y="monto", title="Gastos por Farmacia"), use_container_width=True)

# ---------------------------------
# TOP FARMACIA
# ---------------------------------
st.subheader("🥇 Farmacia con Mayor Venta")

if not df_filt.empty:
    top = df_filt.groupby("farmacia")["ventas_totales"].sum().idxmax()
    total = df_filt.groupby("farmacia")["ventas_totales"].sum().max()
    st.success(f"🥇 {top} — ${total:,.2f}")

# ---------------------------------
# REPORTE DESCARGABLE
# ---------------------------------


# ---------------------------------
# REPORTE PDF
# ---------------------------------
if st.button("📄 Generar Reporte PDF"):
    pdf = generar_reporte_financiero(
        df_filt,
        df_gastos_filt,
        periodo_kpi
    )

    st.download_button(
        "⬇️ Descargar Reporte",
        pdf,
        file_name=f"reporte_financiero_{periodo_kpi.replace(' ', '_')}.pdf",
        mime="application/pdf"
    )

# ---------------------------------
# SIDEBAR
# ---------------------------------
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button(" Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")
