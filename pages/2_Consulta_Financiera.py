import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
# ===============================
# FECHA ACTUAL (DEFAULT FILTROS)
# ===============================
hoy = datetime.today()
anio_actual = hoy.year
mes_actual = hoy.month

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

if st.session_state["usuario"]["rol"] != "admin":
    st.error("No tienes permisos para esta sección")
    st.stop()
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

if anio_actual in anios:
    index_anio = anios.index(anio_actual)
else:
    index_anio = 0

anio_sel = st.sidebar.selectbox(
    "Año",
    anios,
    index=index_anio
)


meses = ["Todos"] + [
    f"{m} - {MESES_ES[m]}" for m in sorted(df_ventas["fecha"].dt.month.unique())
]

mes_actual_label = f"{mes_actual} - {MESES_ES[mes_actual]}"

if mes_actual_label in meses:
    index_mes = meses.index(mes_actual_label)
else:
    index_mes = 0

mes_sel = st.sidebar.selectbox(
    "Mes",
    meses,
    index=index_mes
)


# ===============================
# APLICAR FILTROS
# ===============================
df_ventas_filt = df_ventas.copy()
df_gastos_filt = df_gastos.copy()

mes_num = None
if mes_sel != "Todos":
    mes_num = int(mes_sel.split(" - ")[0])

if farmacia_sel != "Todas":
    df_ventas_filt = df_ventas_filt[df_ventas_filt["farmacia"] == farmacia_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["farmacia"] == farmacia_sel]

if anio_sel != "Todos":
    df_ventas_filt = df_ventas_filt[df_ventas_filt["fecha"].dt.year == anio_sel]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.year == anio_sel]

if mes_num is not None:
    df_ventas_filt = df_ventas_filt[df_ventas_filt["fecha"].dt.month == mes_num]
    df_gastos_filt = df_gastos_filt[df_gastos_filt["fecha"].dt.month == mes_num]

# ===============================


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
tab_ventas, tab_gastos, tab_resumen, tab_consulta = st.tabs(
    ["🟢 Ventas", "🔴 Gastos", "🔵 Resumen","📊 Consulta Específica"]
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

#
# CONSULTA ESPECIFICA
#
with tab_consulta:

    st.subheader("📊 Consulta Específica")

    fecha_inicio = st.date_input(
        "Fecha inicio",
        key="consulta_inicio"
    )

    fecha_fin = st.date_input(
        "Fecha fin",
        key="consulta_fin"
    )

    farmacias_consulta = st.multiselect(
        "Farmacias",
        sorted(df_ventas["farmacia"].unique()),
        default=sorted(df_ventas["farmacia"].unique())
    )

    df_v_consulta = df_ventas[
        (df_ventas["fecha"] >= pd.to_datetime(fecha_inicio)) &
        (df_ventas["fecha"] <= pd.to_datetime(fecha_fin)) &
        (df_ventas["farmacia"].isin(farmacias_consulta))
    ]

    df_g_consulta = df_gastos[
        (df_gastos["fecha"] >= pd.to_datetime(fecha_inicio)) &
        (df_gastos["fecha"] <= pd.to_datetime(fecha_fin)) &
        (df_gastos["farmacia"].isin(farmacias_consulta))
    ]

    ventas_total = df_v_consulta["ventas_totales"].sum()
    gastos_total = df_g_consulta["monto"].sum()
    utilidad = ventas_total - gastos_total

    c1,c2,c3 = st.columns(3)

    c1.metric(
        "Ventas Totales",
        f"${ventas_total:,.2f}"
    )

    c2.metric(
        "Gastos Totales",
        f"${gastos_total:,.2f}"
    )

    c3.metric(
        "Utilidad Neta",
        f"${utilidad:,.2f}"
    )

    ventas_farmacia = (
        df_v_consulta
        .groupby("farmacia")["ventas_totales"]
        .sum()
        .reset_index()
    )

    ventas_farmacia.columns = [
        "Farmacia",
        "Ventas"
    ]

    st.subheader("🏪 Ventas por Farmacia")

    st.dataframe(
        ventas_farmacia,
        use_container_width=True,
        hide_index=True
    )

    gastos_farmacia = (
        df_g_consulta
        .groupby("farmacia")["monto"]
        .sum()
        .reset_index()
    )

    gastos_farmacia.columns = [
        "Farmacia",
        "Gastos"
    ]

    st.subheader("💸 Gastos por Farmacia")

    st.dataframe(
        gastos_farmacia,
        use_container_width=True,
        hide_index=True
    )

    utilidad_farmacia = (
        ventas_farmacia
        .merge(
            gastos_farmacia,
            on="Farmacia",
            how="left"
        )
    )

    utilidad_farmacia["Gastos"] = utilidad_farmacia["Gastos"].fillna(0)

    utilidad_farmacia["Utilidad"] = (
        utilidad_farmacia["Ventas"]
        - utilidad_farmacia["Gastos"]
    )

    st.subheader("📈 Utilidad por Farmacia")

    st.dataframe(
        utilidad_farmacia,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("🧾 Desglose de Gastos")

    desglose = (
        df_g_consulta
        .groupby("categoria")["monto"]
        .sum()
        .reset_index()
        .sort_values("monto", ascending=False)
    )

    st.dataframe(
        desglose,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📋 Gastos Detallados")

    st.dataframe(
    df_g_consulta[
        [
            "fecha",
            "farmacia",
            "categoria",
            "descripcion",
            "monto"
        ]
    ].sort_values("fecha"),
    use_container_width=True,
    hide_index=True,
    column_config={
        "fecha": st.column_config.DateColumn("Fecha"),
        "farmacia": st.column_config.TextColumn("Farmacia"),
        "categoria": st.column_config.TextColumn("Categoría"),
        "descripcion": st.column_config.TextColumn("Descripción"),
        "monto": st.column_config.NumberColumn(
            "Monto ($)",
            format="$%.2f"
        ),
    }
)

    import plotly.express as px

    fig = px.bar(
        utilidad_farmacia,
        x="Farmacia",
        y="Utilidad",
        title="Utilidad por Farmacia"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
    st.divider()

    st.subheader("📥 Exportar Consulta")

    if st.button("📊 Generar Excel"):

        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:

            # ==========================
            # RESUMEN GENERAL
            # ==========================
            resumen_df = pd.DataFrame({
                "Concepto": [
                    "Ventas Totales",
                    "Gastos Totales",
                    "Utilidad Neta"
                ],
                "Monto": [
                    ventas_total,
                    gastos_total,
                    utilidad
                ]
            })

            resumen_df.to_excel(
                writer,
                sheet_name="Resumen",
                index=False
            )

            # ==========================
            # VENTAS POR FARMACIA
            # ==========================
            ventas_farmacia.to_excel(
                writer,
                sheet_name="Ventas por Farmacia",
                index=False
            )

            # ==========================
            # GASTOS POR FARMACIA
            # ==========================
            gastos_farmacia.to_excel(
                writer,
                sheet_name="Gastos por Farmacia",
                index=False
            )

            # ==========================
            # UTILIDAD POR FARMACIA
            # ==========================
            utilidad_farmacia.to_excel(
                writer,
                sheet_name="Utilidad por Farmacia",
                index=False
            )

            # ==========================
            # DESGLOSE DE GASTOS
            # ==========================
            desglose.to_excel(
                writer,
                sheet_name="Desglose Gastos",
                index=False
            )

            # ==========================
            # GASTOS DETALLADOS
            # ==========================
            df_g_consulta[
                [
                    "fecha",
                    "farmacia",
                    "categoria",
                    "tipo_gasto",
                    "descripcion",
                    "monto"
                ]
            ].to_excel(
                writer,
                sheet_name="Gastos Detallados",
                index=False
            )

            # ==========================
            # VENTAS DETALLADAS
            # ==========================
            df_v_consulta[
                [
                    "fecha",
                    "farmacia",
                    "ventas_totales"
                ]
            ].to_excel(
                writer,
                sheet_name="Ventas Detalladas",
                index=False
            )

        excel_data = output.getvalue()

        st.download_button(
            label="⬇️ Descargar Excel",
            data=excel_data,
            file_name=f"consulta_financiera_{fecha_inicio}_{fecha_fin}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
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
    st.switch_page("streamlit_app.py")
