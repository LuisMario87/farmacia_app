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
from utils.permisos import validar_acceso_pagina
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
validar_acceso_pagina(conn, "consulta_financiera")
df_ventas = pd.read_sql("""
    SELECT 
        v.venta_id,
        f.nombre AS farmacia,

        COALESCE(
            v.ventas_totales,
            0
        ) AS ventas_totales,

        COALESCE(
            v.venta_tarjeta,
            0
        ) AS venta_tarjeta,

        GREATEST(
            COALESCE(v.ventas_totales, 0)
            - COALESCE(v.venta_tarjeta, 0),
            0
        ) AS venta_efectivo,

        v.tipo_registro,
        v.fecha

    FROM ventas v

    JOIN farmacias f
        ON v.farmacia_id = f.farmacia_id

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
# SIDEBAR INFO
# ===============================
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")



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

# ==================================================
# CONSULTA ESPECÍFICA
# ==================================================

with tab_consulta:

    st.subheader("Consulta específica")

    # ==================================================
    # FILTROS
    # ==================================================

    fecha_inicio = st.date_input(
        "Fecha inicio",
        key="consulta_inicio"
    )

    fecha_fin = st.date_input(
        "Fecha fin",
        key="consulta_fin"
    )

    farmacias_disponibles = sorted(
        set(df_ventas["farmacia"].dropna().tolist())
        | set(df_gastos["farmacia"].dropna().tolist())
    )

    farmacias_consulta = st.multiselect(
        "Farmacias",
        farmacias_disponibles,
        default=farmacias_disponibles,
        key="consulta_farmacias"
    )

    if fecha_inicio > fecha_fin:

        st.error(
            "La fecha de inicio no puede ser posterior a la fecha final."
        )

    elif not farmacias_consulta:

        st.warning(
            "Selecciona al menos una farmacia para realizar la consulta."
        )

    else:

        # ==================================================
        # FILTRAR VENTAS Y GASTOS
        # ==================================================

        fecha_inicio_ts = pd.to_datetime(fecha_inicio)
        fecha_fin_ts = pd.to_datetime(fecha_fin)

        df_v_consulta = df_ventas[
            (df_ventas["fecha"] >= fecha_inicio_ts)
            & (df_ventas["fecha"] <= fecha_fin_ts)
            & (df_ventas["farmacia"].isin(farmacias_consulta))
        ].copy()

        df_g_consulta = df_gastos[
            (df_gastos["fecha"] >= fecha_inicio_ts)
            & (df_gastos["fecha"] <= fecha_fin_ts)
            & (df_gastos["farmacia"].isin(farmacias_consulta))
        ].copy()

        columnas_ventas_numericas = [
            "ventas_totales",
            "venta_efectivo",
            "venta_tarjeta"
        ]

        for columna in columnas_ventas_numericas:

            df_v_consulta[columna] = pd.to_numeric(
                df_v_consulta[columna],
                errors="coerce"
            ).fillna(0)

        df_g_consulta["monto"] = pd.to_numeric(
            df_g_consulta["monto"],
            errors="coerce"
        ).fillna(0)

        # ==================================================
        # TOTALES
        # ==================================================

        ventas_total = df_v_consulta["ventas_totales"].sum()

        ventas_efectivo_total = (
            df_v_consulta["venta_efectivo"].sum()
        )

        ventas_tarjeta_total = (
            df_v_consulta["venta_tarjeta"].sum()
        )

        gastos_total = df_g_consulta["monto"].sum()

        utilidad = ventas_total - gastos_total

        porcentaje_tarjeta = (
            ventas_tarjeta_total / ventas_total * 100
            if ventas_total > 0
            else 0
        )

        diferencia_desglose = (
            ventas_total
            - ventas_efectivo_total
            - ventas_tarjeta_total
        )

        # ==================================================
        # MÉTRICAS DE VENTAS
        # ==================================================

        st.markdown("### Resumen de ventas")

        c1, c2, c3 = st.columns(3)

        with c1:

            st.metric(
                "Ventas totales",
                f"${ventas_total:,.2f}"
            )

        with c2:

            st.metric(
                "Ventas en efectivo",
                f"${ventas_efectivo_total:,.2f}"
            )

        with c3:

            st.metric(
                "Ventas con tarjeta",
                f"${ventas_tarjeta_total:,.2f}",
                delta=f"{porcentaje_tarjeta:.2f}% del total",
                delta_color="off"
            )

        c1, c2 = st.columns(2)

        with c1:

            st.metric(
                "Gastos totales",
                f"${gastos_total:,.2f}"
            )

        with c2:

            st.metric(
                "Utilidad neta",
                f"${utilidad:,.2f}"
            )

        st.caption(
            f"Comprobación de ventas: "
            f"${ventas_efectivo_total:,.2f} en efectivo "
            f"+ ${ventas_tarjeta_total:,.2f} con tarjeta "
            f"= ${ventas_total:,.2f} en ventas totales."
        )

        if abs(diferencia_desglose) > 0.01:

            st.warning(
                "Existe una diferencia entre las ventas totales y el "
                "desglose de efectivo y tarjeta. "
                f"Diferencia detectada: ${diferencia_desglose:,.2f}"
            )

        st.divider()

        # ==================================================
        # DESGLOSE POR MÉTODO DE PAGO
        # ==================================================

        st.subheader("Desglose de ventas por método de pago")

        desglose_metodo_pago = pd.DataFrame({
            "Método de pago": [
                "Efectivo",
                "Tarjeta"
            ],
            "Monto": [
                ventas_efectivo_total,
                ventas_tarjeta_total
            ]
        })

        desglose_metodo_pago["Porcentaje"] = (
            desglose_metodo_pago["Monto"] / ventas_total * 100
            if ventas_total > 0
            else 0
        )

        st.dataframe(
            desglose_metodo_pago,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Método de pago": st.column_config.TextColumn(
                    "Método de pago"
                ),
                "Monto": st.column_config.NumberColumn(
                    "Monto",
                    format="$%.2f"
                ),
                "Porcentaje": st.column_config.NumberColumn(
                    "Porcentaje",
                    format="%.2f %%"
                )
            }
        )

        st.divider()

        # ==================================================
        # VENTAS POR FARMACIA
        # ==================================================

        st.subheader("Ventas por farmacia")

        if df_v_consulta.empty:

            ventas_farmacia = pd.DataFrame(columns=[
                "Farmacia",
                "Ventas",
                "Efectivo",
                "Tarjeta",
                "Porcentaje Tarjeta"
            ])

            st.info(
                "No hay ventas registradas para la consulta seleccionada."
            )

        else:

            ventas_farmacia = (
                df_v_consulta
                .groupby(
                    "farmacia",
                    as_index=False
                )
                .agg(
                    Ventas=("ventas_totales", "sum"),
                    Efectivo=("venta_efectivo", "sum"),
                    Tarjeta=("venta_tarjeta", "sum")
                )
                .rename(columns={
                    "farmacia": "Farmacia"
                })
            )

            ventas_farmacia["Porcentaje Tarjeta"] = (
                ventas_farmacia.apply(
                    lambda fila: (
                        fila["Tarjeta"] / fila["Ventas"] * 100
                        if fila["Ventas"] > 0
                        else 0
                    ),
                    axis=1
                )
            )

            ventas_farmacia = ventas_farmacia.sort_values(
                "Ventas",
                ascending=False
            )

            st.dataframe(
                ventas_farmacia,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Farmacia": st.column_config.TextColumn(
                        "Farmacia"
                    ),
                    "Ventas": st.column_config.NumberColumn(
                        "Ventas totales",
                        format="$%.2f"
                    ),
                    "Efectivo": st.column_config.NumberColumn(
                        "Efectivo",
                        format="$%.2f"
                    ),
                    "Tarjeta": st.column_config.NumberColumn(
                        "Tarjeta",
                        format="$%.2f"
                    ),
                    "Porcentaje Tarjeta":
                        st.column_config.NumberColumn(
                            "% con tarjeta",
                            format="%.2f %%"
                        )
                }
            )

        # ==================================================
        # VENTAS DETALLADAS
        # ==================================================

        st.subheader("Ventas detalladas")

        if df_v_consulta.empty:

            st.info(
                "No hay ventas detalladas para mostrar."
            )

        else:

            ventas_detalladas = df_v_consulta[
                [
                    "fecha",
                    "farmacia",
                    "ventas_totales",
                    "venta_efectivo",
                    "venta_tarjeta"
                ]
            ].copy()

            ventas_detalladas = ventas_detalladas.sort_values(
                [
                    "fecha",
                    "farmacia"
                ],
                ascending=[
                    True,
                    True
                ]
            )

            st.dataframe(
                ventas_detalladas,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fecha": st.column_config.DateColumn(
                        "Fecha",
                        format="DD/MM/YYYY"
                    ),
                    "farmacia": st.column_config.TextColumn(
                        "Farmacia"
                    ),
                    "ventas_totales":
                        st.column_config.NumberColumn(
                            "Ventas totales",
                            format="$%.2f"
                        ),
                    "venta_efectivo":
                        st.column_config.NumberColumn(
                            "Efectivo",
                            format="$%.2f"
                        ),
                    "venta_tarjeta":
                        st.column_config.NumberColumn(
                            "Tarjeta",
                            format="$%.2f"
                        )
                }
            )

        st.divider()

        # ==================================================
        # GASTOS POR FARMACIA
        # ==================================================

        st.subheader("Gastos por farmacia")

        if df_g_consulta.empty:

            gastos_farmacia = pd.DataFrame(columns=[
                "Farmacia",
                "Gastos"
            ])

            st.info(
                "No hay gastos registrados para la consulta seleccionada."
            )

        else:

            gastos_farmacia = (
                df_g_consulta
                .groupby(
                    "farmacia",
                    as_index=False
                )["monto"]
                .sum()
                .rename(columns={
                    "farmacia": "Farmacia",
                    "monto": "Gastos"
                })
                .sort_values(
                    "Gastos",
                    ascending=False
                )
            )

            st.dataframe(
                gastos_farmacia,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Farmacia": st.column_config.TextColumn(
                        "Farmacia"
                    ),
                    "Gastos": st.column_config.NumberColumn(
                        "Gastos",
                        format="$%.2f"
                    )
                }
            )

        # ==================================================
        # UTILIDAD POR FARMACIA
        # ==================================================

        st.subheader("Utilidad por farmacia")

        utilidad_farmacia = (
            ventas_farmacia[
                [
                    "Farmacia",
                    "Ventas",
                    "Efectivo",
                    "Tarjeta"
                ]
            ]
            .merge(
                gastos_farmacia,
                on="Farmacia",
                how="outer"
            )
        )

        columnas_utilidad = [
            "Ventas",
            "Efectivo",
            "Tarjeta",
            "Gastos"
        ]

        for columna in columnas_utilidad:

            utilidad_farmacia[columna] = (
                utilidad_farmacia[columna]
                .fillna(0)
            )

        utilidad_farmacia["Utilidad"] = (
            utilidad_farmacia["Ventas"]
            - utilidad_farmacia["Gastos"]
        )

        utilidad_farmacia["Margen (%)"] = (
            utilidad_farmacia.apply(
                lambda fila: (
                    fila["Utilidad"] / fila["Ventas"] * 100
                    if fila["Ventas"] > 0
                    else 0
                ),
                axis=1
            )
        )

        utilidad_farmacia = utilidad_farmacia.sort_values(
            "Utilidad",
            ascending=False
        )

        st.dataframe(
            utilidad_farmacia,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Farmacia": st.column_config.TextColumn(
                    "Farmacia"
                ),
                "Ventas": st.column_config.NumberColumn(
                    "Ventas totales",
                    format="$%.2f"
                ),
                "Efectivo": st.column_config.NumberColumn(
                    "Efectivo",
                    format="$%.2f"
                ),
                "Tarjeta": st.column_config.NumberColumn(
                    "Tarjeta",
                    format="$%.2f"
                ),
                "Gastos": st.column_config.NumberColumn(
                    "Gastos",
                    format="$%.2f"
                ),
                "Utilidad": st.column_config.NumberColumn(
                    "Utilidad",
                    format="$%.2f"
                ),
                "Margen (%)": st.column_config.NumberColumn(
                    "Margen",
                    format="%.2f %%"
                )
            }
        )

        st.divider()

        # ==================================================
        # DESGLOSE DE GASTOS
        # ==================================================

        st.subheader("Desglose de gastos")

        if df_g_consulta.empty:

            desglose = pd.DataFrame(columns=[
                "categoria",
                "monto"
            ])

            st.info(
                "No hay gastos para desglosar."
            )

        else:

            desglose = (
                df_g_consulta
                .groupby(
                    "categoria",
                    as_index=False
                )["monto"]
                .sum()
                .sort_values(
                    "monto",
                    ascending=False
                )
            )

            st.dataframe(
                desglose,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "categoria": st.column_config.TextColumn(
                        "Categoría"
                    ),
                    "monto": st.column_config.NumberColumn(
                        "Monto",
                        format="$%.2f"
                    )
                }
            )

        # ==================================================
        # GASTOS DETALLADOS
        # ==================================================

        st.subheader("Gastos detallados")

        if df_g_consulta.empty:

            st.info(
                "No hay gastos detallados para mostrar."
            )

        else:

            gastos_detallados = df_g_consulta[
                [
                    "fecha",
                    "farmacia",
                    "categoria",
                    "descripcion",
                    "monto"
                ]
            ].copy()

            gastos_detallados = gastos_detallados.sort_values(
                [
                    "fecha",
                    "farmacia"
                ]
            )

            st.dataframe(
                gastos_detallados,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "fecha": st.column_config.DateColumn(
                        "Fecha",
                        format="DD/MM/YYYY"
                    ),
                    "farmacia": st.column_config.TextColumn(
                        "Farmacia"
                    ),
                    "categoria": st.column_config.TextColumn(
                        "Categoría"
                    ),
                    "descripcion": st.column_config.TextColumn(
                        "Descripción"
                    ),
                    "monto": st.column_config.NumberColumn(
                        "Monto",
                        format="$%.2f"
                    )
                }
            )

        st.divider()

        # ==================================================
        # EXPORTAR CONSULTA
        # ==================================================

        st.subheader("Exportar consulta")

        if st.button(
            "Generar Excel",
            key="consulta_generar_excel"
        ):

            output = BytesIO()

            with pd.ExcelWriter(
                output,
                engine="openpyxl"
            ) as writer:

                # ==========================================
                # RESUMEN GENERAL
                # ==========================================

                resumen_df = pd.DataFrame({
                    "Concepto": [
                        "Ventas Totales",
                        "Ventas en Efectivo",
                        "Ventas con Tarjeta",
                        "Gastos Totales",
                        "Utilidad Neta"
                    ],
                    "Monto": [
                        ventas_total,
                        ventas_efectivo_total,
                        ventas_tarjeta_total,
                        gastos_total,
                        utilidad
                    ]
                })

                resumen_df.to_excel(
                    writer,
                    sheet_name="Resumen",
                    index=False
                )

                # ==========================================
                # MÉTODOS DE PAGO
                # ==========================================

                desglose_metodo_pago.to_excel(
                    writer,
                    sheet_name="Métodos de Pago",
                    index=False
                )

                # ==========================================
                # VENTAS POR FARMACIA
                # ==========================================

                ventas_farmacia.to_excel(
                    writer,
                    sheet_name="Ventas por Farmacia",
                    index=False
                )

                # ==========================================
                # VENTAS DETALLADAS
                # ==========================================

                df_v_consulta[
                    [
                        "fecha",
                        "farmacia",
                        "ventas_totales",
                        "venta_efectivo",
                        "venta_tarjeta"
                    ]
                ].sort_values(
                    [
                        "fecha",
                        "farmacia"
                    ]
                ).to_excel(
                    writer,
                    sheet_name="Ventas Detalladas",
                    index=False
                )

                # ==========================================
                # GASTOS POR FARMACIA
                # ==========================================

                gastos_farmacia.to_excel(
                    writer,
                    sheet_name="Gastos por Farmacia",
                    index=False
                )

                # ==========================================
                # UTILIDAD POR FARMACIA
                # ==========================================

                utilidad_farmacia.to_excel(
                    writer,
                    sheet_name="Utilidad por Farmacia",
                    index=False
                )

                # ==========================================
                # DESGLOSE DE GASTOS
                # ==========================================

                desglose.to_excel(
                    writer,
                    sheet_name="Desglose Gastos",
                    index=False
                )

                # ==========================================
                # GASTOS DETALLADOS
                # ==========================================

                df_g_consulta[
                    [
                        "fecha",
                        "farmacia",
                        "categoria",
                        "tipo_gasto",
                        "descripcion",
                        "monto"
                    ]
                ].sort_values(
                    [
                        "fecha",
                        "farmacia"
                    ]
                ).to_excel(
                    writer,
                    sheet_name="Gastos Detallados",
                    index=False
                )

            excel_data = output.getvalue()

            st.session_state[
                "excel_consulta_financiera"
            ] = excel_data

        if (
            "excel_consulta_financiera"
            in st.session_state
        ):

            st.download_button(
                label="Descargar Excel",
                data=st.session_state[
                    "excel_consulta_financiera"
                ],
                file_name=(
                    f"consulta_financiera_"
                    f"{fecha_inicio}_{fecha_fin}.xlsx"
                ),
                mime=(
                    "application/"
                    "vnd.openxmlformats-officedocument."
                    "spreadsheetml.sheet"
                ),
                key="consulta_descargar_excel"
            )