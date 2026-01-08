import streamlit as st
import pandas as pd
from utils.conexionASupabase import get_connection
from reports.pdf_gastos import generar_pdf_gastos
from reports.pdf_resumen import generar_pdf_resumen_financiero


# ===============================
# CONFIG
# ===============================
st.set_page_config(page_title="Consulta Financiera", layout="wide")
st.title("📄 Consulta Financiera")

# ===============================
# SEGURIDAD
# ===============================
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

# ===============================
# CONEXIÓN
# ===============================
conn = get_connection()

df_ventas = pd.read_sql("""
SELECT 
    v.venta_id,
    f.nombre AS farmacia,
    v.ventas_totales,
    v.tipo_registro,
    v.fecha
FROM ventas v
JOIN farmacias f ON v.farmacia_id = f.farmacia_id
ORDER BY v.fecha DESC;
""", conn)

df_gastos = pd.read_sql("""
SELECT
    g.gasto_id,
    f.nombre AS farmacia,
    g.monto,
    g.fecha,
    g.tipo_gasto,
    g.categoria,
    g.descripcion
FROM gastos g
JOIN farmacias f ON g.farmacia_id = f.farmacia_id
ORDER BY g.fecha DESC;
""", conn)

conn.close()

df_ventas["fecha"] = pd.to_datetime(df_ventas["fecha"])
df_gastos["fecha"] = pd.to_datetime(df_gastos["fecha"])

# ===============================
# TRADUCCIONES MES
# ===============================

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
# ===============================
# SESSION STATE
# ===============================

if "pdf_gastos" not in st.session_state:
    st.session_state["pdf_gastos"] = None

if "pdf_resumen" not in st.session_state:
    st.session_state["pdf_resumen"] = None


# ===============================
# FILTROS
# ===============================
st.sidebar.header("🔎 Filtros")

farmacias = ["Todas"] + sorted(df_ventas["farmacia"].unique())
farmacia_sel = st.sidebar.selectbox("Farmacia", farmacias)

anios = ["Todos"] + sorted(df_ventas["fecha"].dt.year.unique())
anio_sel = st.sidebar.selectbox("Año", anios)

meses = ["Todos"] + list(range(1, 13))
mes_sel = st.sidebar.selectbox("Mes", meses)

# ===============================
# APLICAR FILTROS
# ===============================
df_ventas_filt = df_ventas.copy()
df_gastos_filt = df_gastos.copy()

if farmacia_sel != "Todas":
    df_ventas_filt = df_ventas_filt[df_ventas_filt["farmacia"] == farmacia_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_ventas_filt = df_ventas_filt[df_ventas_filt["fecha"].dt.year == anio_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.year == anio_sel]

if mes_sel != "Todos":
    df_ventas_filt = df_ventas_filt[df_ventas_filt["fecha"].dt.month == mes_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.month == mes_sel]

# ---------------------------------
# FILTRADO
# ---------------------------------
df_filt = df_ventas.copy()
df_gastos_filt = df_gastos.copy()

if farmacia_sel != "Todas":
    df_filt = df_filt[df_filt["farmacia"] == farmacia_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_filt = df_filt[df_filt["fecha"].dt.year == anio_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.year == anio_sel]

mes_num = None
if mes_sel != "Todos":
    mes_num = mes_sel
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

# ===============================
# TABS
# ===============================
tab_ventas, tab_gastos, tab_resumen = st.tabs(
    ["🟢 Ventas", "🔴 Gastos", "🔵 Resumen"]
)

# ===============================
# 🟢 VENTAS
# ===============================
with tab_ventas:
    st.subheader("🟢 Ventas registradas")

    col1, col2 = st.columns([2, 1])

    with col1:
        busqueda = st.text_input("🔍 Buscar farmacia")

    with col2:
        page_size = st.selectbox("Filas por página", [10, 20, 50], key="v_ps")

    if busqueda:
        df_v = df_ventas_filt[
            df_ventas_filt["farmacia"]
            .str.contains(busqueda, case=False, na=False)
        ]
    else:
        df_v = df_ventas_filt.copy()

    df_v = df_v.sort_values("fecha", ascending=False)

    total = len(df_v)
    total_pages = max(1, (total - 1) // page_size + 1)

    page = st.number_input(
        "Página",
        1,
        total_pages,
        1,
        key="v_page"
    )

    start = (page - 1) * page_size
    end = start + page_size

    st.dataframe(df_v.iloc[start:end], use_container_width=True, hide_index=True)

    st.caption(f"Página {page} de {total_pages}")

# ===============================
# 🔴 GASTOS
# ===============================
with tab_gastos:
    st.subheader("🔴 Gastos registrados")

    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        buscar_desc = st.text_input("🔍 Buscar descripción")

    with c2:
        categorias = ["Todas"] + sorted(df_gastos_filt["categoria"].dropna().unique())
        cat_sel = st.selectbox("Categoría", categorias)

    with c3:
        page_size = st.selectbox("Filas por página", [10, 20, 50], key="g_ps")

    df_g = df_gastos_filt.copy()

    if buscar_desc:
        df_g = df_g[df_g["descripcion"].str.contains(buscar_desc, case=False, na=False)]

    if cat_sel != "Todas":
        df_g = df_g[df_g["categoria"] == cat_sel]

    df_g = df_g.sort_values("fecha", ascending=False)

    total = len(df_g)
    total_pages = max(1, (total - 1) // page_size + 1)

    page = st.number_input(
        "Página",
        1,
        total_pages,
        1,
        key="g_page"
    )

    start = (page - 1) * page_size
    end = start + page_size

    st.dataframe(df_g.iloc[start:end], use_container_width=True, hide_index=True)

    st.caption(f"Página {page} de {total_pages}")

    if st.button("📄 Generar Reporte de Gastos (PDF)"):
        st.session_state["pdf_gastos"] = generar_pdf_gastos(
            df_gastos_filt,
            periodo_kpi,
            farmacia_sel
    )

    if st.session_state["pdf_gastos"] is not None:
        st.download_button(
            "⬇️ Descargar PDF",
            st.session_state["pdf_gastos"],
            file_name="reporte_gastos.pdf",
            mime="application/pdf"
    )



# ===============================
# 🔵 RESUMEN
# ===============================
with tab_resumen:
    st.subheader("🔵 Resumen del periodo")

    ventas_total = df_ventas_filt["ventas_totales"].sum()
    gastos_total = df_gastos_filt["monto"].sum()
    utilidad = ventas_total - gastos_total

    st.write(f"🟢 Ventas totales: **${ventas_total:,.2f}**")
    st.write(f"🔴 Gastos totales: **${gastos_total:,.2f}**")
    st.write(f"🔵 Utilidad: **${utilidad:,.2f}**")

    if st.button("📄 Generar Resumen Financiero (PDF)"):
        st.session_state["pdf_resumen"] = generar_pdf_resumen_financiero(
            df_ventas_filt,
            df_gastos_filt,
            periodo_kpi,
            farmacia_sel
    )

    if st.session_state["pdf_resumen"] is not None:
        st.download_button(
            "⬇️ Descargar Resumen Financiero",
            st.session_state["pdf_resumen"],
            file_name="resumen_financiero.pdf",
            mime="application/pdf"
        )

# ===============================
# SIDEBAR INFO
# ===============================
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("login.py")
