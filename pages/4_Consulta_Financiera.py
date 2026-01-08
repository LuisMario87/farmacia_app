import streamlit as st
import pandas as pd
from utils.conexionASupabase import get_connection

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
