import streamlit as st
import pandas as pd
from utils.conexionASupabase import get_connection

st.set_page_config(page_title="Consulta Financiera", layout="wide")
st.title("📄 Consulta Financiera")

# Seguridad
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

# -------------------------------
# CARGA DE DATOS
# -------------------------------
conn = get_connection()

df_ventas = pd.read_sql("""
SELECT v.venta_id, f.nombre AS farmacia, v.fecha, v.ventas_totales
FROM ventas v
JOIN farmacias f ON v.farmacia_id = f.farmacia_id
ORDER BY v.fecha DESC;
""", conn)

df_gastos = pd.read_sql("""
SELECT g.gasto_id, f.nombre AS farmacia, g.fecha, g.monto, g.descripcion, g.categoria
FROM gastos g
JOIN farmacias f ON g.farmacia_id = f.farmacia_id
ORDER BY g.fecha DESC;
""", conn)

conn.close()

df_ventas["fecha"] = pd.to_datetime(df_ventas["fecha"])
df_gastos["fecha"] = pd.to_datetime(df_gastos["fecha"])

# -------------------------------
# FILTROS
#------------------------------

st.sidebar.header("🔎 Filtros")

farmacias = ["Todas"] + sorted(df_ventas["farmacia"].unique())
farmacia_sel = st.sidebar.selectbox("Farmacia", farmacias)

anios = ["Todos"] + sorted(df_ventas["fecha"].dt.year.unique())
anio_sel = st.sidebar.selectbox("Año", anios)

meses = ["Todos"] + list(range(1, 13))
mes_sel = st.sidebar.selectbox("Mes", meses)

def aplicar_filtros(df):
    if farmacia_sel != "Todas":
        df = df[df["farmacia"] == farmacia_sel]
    if anio_sel != "Todos":
        df = df[df["fecha"].dt.year == anio_sel]
    if mes_sel != "Todos":
        df = df[df["fecha"].dt.month == mes_sel]
    return df

df_ventas_filt = aplicar_filtros(df_ventas)
df_gastos_filt = aplicar_filtros(df_gastos)
# -------------------------------
# VISUALIZACIÓN DE DATOS    
# -------------------------------

tab_ventas, tab_gastos, tab_resumen = st.tabs(
    ["🟢 Ventas", "🔴 Gastos", "🔵 Resumen"]
)

with tab_ventas:
    st.subheader("🟢 Ventas Registradas")

    st.metric(
        "Total Ventas",
        f"${df_ventas_filt['ventas_totales'].sum():,.2f}"
    )

    st.dataframe(
        df_ventas_filt,
        use_container_width=True
    )

    # Exportar
    st.download_button(
        "⬇️ Descargar Ventas (CSV)",
        df_ventas_filt.to_csv(index=False),
        file_name="ventas.csv",
        mime="text/csv"
    )

with tab_gastos:
    st.subheader("🔴 Gastos Registrados")

    st.metric(
        "Total Gastos",
        f"${df_gastos_filt['monto'].sum():,.2f}"
    )

    st.dataframe(
        df_gastos_filt,
        use_container_width=True
    )

    st.download_button(
        "⬇️ Descargar Gastos (CSV)",
        df_gastos_filt.to_csv(index=False),
        file_name="gastos.csv",
        mime="text/csv"
    )

with tab_resumen:
    ventas = df_ventas_filt["ventas_totales"].sum()
    gastos = df_gastos_filt["monto"].sum()
    utilidad = ventas - gastos

    c1, c2, c3 = st.columns(3)
    c1.metric("Ventas", f"${ventas:,.2f}")
    c2.metric("Gastos", f"${gastos:,.2f}")
    c3.metric("Utilidad", f"${utilidad:,.2f}")
