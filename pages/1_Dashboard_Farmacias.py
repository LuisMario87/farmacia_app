import streamlit as st
import pandas as pd
import plotly.express as px

from datetime import datetime, timedelta, date
from calendar import monthrange

from utils.conexionASupabase import get_connection
from utils.permisos import validar_acceso_pagina
from reports.reporte_financiero import generar_reporte_financiero


st.set_page_config(
    page_title="Dashboard",
    layout="wide"
)


# ==================================================
# SEGURIDAD
# ==================================================

if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")


# ==================================================
# CONEXIÓN Y VALIDACIÓN DE PERMISOS
# ==================================================

conn = get_connection()

validar_acceso_pagina(
    conn,
    "dashboard"
)


# ==================================================
# FUNCIONES AUXILIARES
# ==================================================

MESES_ES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
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

DIAS_ES = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo"
}


def formato_moneda(valor):
    if pd.isna(valor):
        valor = 0

    return f"${valor:,.2f}"


def formato_porcentaje(valor):
    if pd.isna(valor):
        valor = 0

    return f"{valor:.2f}%"


def calcular_variacion(actual, anterior):
    if anterior is None or pd.isna(anterior) or anterior == 0:
        return None

    return ((actual - anterior) / anterior) * 100


def texto_delta(actual, anterior):
    variacion = calcular_variacion(actual, anterior)

    if variacion is None:
        return None

    return f"{variacion:+.1f}% vs periodo anterior"


def obtener_fechas_periodo(anio_sel, mes_sel):
    if anio_sel == "Todos":
        return None, None

    anio = int(anio_sel)

    if mes_sel == "Todos":
        fecha_inicio = date(anio, 1, 1)
        fecha_fin = date(anio + 1, 1, 1)
        return fecha_inicio, fecha_fin

    mes = int(str(mes_sel).split(" - ")[0])

    fecha_inicio = date(anio, mes, 1)

    if mes == 12:
        fecha_fin = date(anio + 1, 1, 1)
    else:
        fecha_fin = date(anio, mes + 1, 1)

    return fecha_inicio, fecha_fin


def obtener_periodo_anterior(anio_sel, mes_sel):
    if anio_sel == "Todos":
        return None, None, None

    anio = int(anio_sel)

    if mes_sel == "Todos":
        fecha_inicio = date(anio - 1, 1, 1)
        fecha_fin = date(anio, 1, 1)
        etiqueta = f"Año {anio - 1}"
        return fecha_inicio, fecha_fin, etiqueta

    mes = int(str(mes_sel).split(" - ")[0])

    if mes == 1:
        mes_anterior = 12
        anio_anterior = anio - 1
    else:
        mes_anterior = mes - 1
        anio_anterior = anio

    fecha_inicio = date(anio_anterior, mes_anterior, 1)

    if mes_anterior == 12:
        fecha_fin = date(anio_anterior + 1, 1, 1)
    else:
        fecha_fin = date(anio_anterior, mes_anterior + 1, 1)

    etiqueta = f"{MESES_ES[mes_anterior]} {anio_anterior}"

    return fecha_inicio, fecha_fin, etiqueta


def obtener_etiqueta_periodo(anio_sel, mes_sel, farmacia_sel):
    if anio_sel == "Todos":
        periodo = "Todos los años"

    elif mes_sel == "Todos":
        periodo = f"Año {anio_sel}"

    else:
        mes = int(str(mes_sel).split(" - ")[0])
        periodo = f"{MESES_ES[mes]} {anio_sel}"

    if farmacia_sel != "Todas":
        periodo = f"{farmacia_sel} — {periodo}"

    return periodo


def construir_where(alias_tabla, farmacia_sel, fecha_inicio, fecha_fin):
    condiciones = []
    parametros = []

    if farmacia_sel != "Todas":
        condiciones.append("f.nombre = %s")
        parametros.append(farmacia_sel)

    if fecha_inicio is not None and fecha_fin is not None:
        condiciones.append(f"{alias_tabla}.fecha >= %s")
        parametros.append(fecha_inicio)

        condiciones.append(f"{alias_tabla}.fecha < %s")
        parametros.append(fecha_fin)

    if condiciones:
        where_sql = "WHERE " + " AND ".join(condiciones)
    else:
        where_sql = ""

    return where_sql, parametros


def cargar_ventas(conn, farmacia_sel, fecha_inicio, fecha_fin):
    where_sql, parametros = construir_where(
        "v",
        farmacia_sel,
        fecha_inicio,
        fecha_fin
    )

    query = f"""
        SELECT
            v.venta_id,
            f.farmacia_id,
            f.nombre AS farmacia,
            f.estado AS estado_farmacia,
            COALESCE(v.ventas_totales, 0) AS ventas_totales,
            v.tipo_registro,
            v.fecha
        FROM ventas v
        JOIN farmacias f
            ON v.farmacia_id = f.farmacia_id
        {where_sql}
        ORDER BY v.fecha;
    """

    df = pd.read_sql(
        query,
        conn,
        params=tuple(parametros)
    )

    df["fecha"] = pd.to_datetime(
        df["fecha"],
        errors="coerce"
    )

    return df


def cargar_gastos(conn, farmacia_sel, fecha_inicio, fecha_fin):
    where_sql, parametros = construir_where(
        "g",
        farmacia_sel,
        fecha_inicio,
        fecha_fin
    )

    query = f"""
        SELECT
            g.gasto_id,
            f.farmacia_id,
            f.nombre AS farmacia,
            f.estado AS estado_farmacia,
            COALESCE(g.monto, 0) AS monto,
            g.fecha,
            g.tipo_gasto,
            g.categoria
        FROM gastos g
        JOIN farmacias f
            ON g.farmacia_id = f.farmacia_id
        {where_sql}
        ORDER BY g.fecha;
    """

    df = pd.read_sql(
        query,
        conn,
        params=tuple(parametros)
    )

    df["fecha"] = pd.to_datetime(
        df["fecha"],
        errors="coerce"
    )

    return df


def cargar_catalogos(conn):
    df_farmacias = pd.read_sql("""
        SELECT
            farmacia_id,
            nombre,
            ciudad,
            estado
        FROM farmacias
        ORDER BY nombre;
    """, conn)

    df_anios = pd.read_sql("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha)::INT AS anio
        FROM ventas
        WHERE fecha IS NOT NULL

        UNION

        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha)::INT AS anio
        FROM gastos
        WHERE fecha IS NOT NULL

        ORDER BY anio DESC;
    """, conn)

    return df_farmacias, df_anios


def cargar_meses_disponibles(conn, anio_sel):
    if anio_sel == "Todos":
        df_meses = pd.read_sql("""
            SELECT DISTINCT
                EXTRACT(MONTH FROM fecha)::INT AS mes
            FROM ventas
            WHERE fecha IS NOT NULL

            UNION

            SELECT DISTINCT
                EXTRACT(MONTH FROM fecha)::INT AS mes
            FROM gastos
            WHERE fecha IS NOT NULL

            ORDER BY mes;
        """, conn)

    else:
        df_meses = pd.read_sql("""
            SELECT DISTINCT
                EXTRACT(MONTH FROM fecha)::INT AS mes
            FROM ventas
            WHERE fecha IS NOT NULL
            AND EXTRACT(YEAR FROM fecha)::INT = %s

            UNION

            SELECT DISTINCT
                EXTRACT(MONTH FROM fecha)::INT AS mes
            FROM gastos
            WHERE fecha IS NOT NULL
            AND EXTRACT(YEAR FROM fecha)::INT = %s

            ORDER BY mes;
        """, conn, params=(int(anio_sel), int(anio_sel)))

    meses = df_meses["mes"].dropna().astype(int).tolist()

    if not meses:
        meses = list(range(1, 13))

    return meses


def crear_dataframe_rendimiento(df_ventas, df_gastos, df_farmacias):
    ventas_farmacia = (
        df_ventas
        .groupby("farmacia", as_index=False)["ventas_totales"]
        .sum()
        if not df_ventas.empty
        else pd.DataFrame(columns=["farmacia", "ventas_totales"])
    )

    gastos_farmacia = (
        df_gastos
        .groupby("farmacia", as_index=False)["monto"]
        .sum()
        if not df_gastos.empty
        else pd.DataFrame(columns=["farmacia", "monto"])
    )

    df_rendimiento = ventas_farmacia.merge(
        gastos_farmacia,
        on="farmacia",
        how="outer"
    )

    df_rendimiento["ventas_totales"] = df_rendimiento["ventas_totales"].fillna(0)
    df_rendimiento["monto"] = df_rendimiento["monto"].fillna(0)
    df_rendimiento["utilidad"] = (
        df_rendimiento["ventas_totales"] -
        df_rendimiento["monto"]
    )

    df_rendimiento["margen"] = df_rendimiento.apply(
        lambda row: (
            row["utilidad"] / row["ventas_totales"] * 100
            if row["ventas_totales"] > 0
            else 0
        ),
        axis=1
    )

    df_estados = df_farmacias[["nombre", "estado"]].rename(
        columns={
            "nombre": "farmacia",
            "estado": "estado"
        }
    )

    df_rendimiento = df_rendimiento.merge(
        df_estados,
        on="farmacia",
        how="left"
    )

    df_rendimiento = df_rendimiento.sort_values(
        "utilidad",
        ascending=False
    )

    return df_rendimiento


def validar_registros_faltantes(
    df_ventas,
    df_farmacias,
    farmacia_sel,
    anio_sel,
    mes_sel
):
    if anio_sel == "Todos" or mes_sel == "Todos":
        return None

    anio = int(anio_sel)
    mes = int(str(mes_sel).split(" - ")[0])

    hoy = datetime.today()

    if anio == hoy.year and mes == hoy.month:
        ultimo_dia = hoy.day
    else:
        ultimo_dia = monthrange(anio, mes)[1]

    df_activas = df_farmacias[
        df_farmacias["estado"] == "ACTIVA"
    ].copy()

    if farmacia_sel != "Todas":
        df_activas = df_activas[
            df_activas["nombre"] == farmacia_sel
        ]

    farmacias_validar = sorted(
        df_activas["nombre"].dropna().unique().tolist()
    )

    if not farmacias_validar:
        return pd.DataFrame(columns=["Farmacia", "Fecha"])

    fecha_inicio = datetime(anio, mes, 1)

    fechas_esperadas = []

    for dia in range(ultimo_dia):
        fecha_actual = fecha_inicio + timedelta(days=dia)

        for farmacia in farmacias_validar:
            fechas_esperadas.append(
                (
                    farmacia,
                    fecha_actual.date()
                )
            )

    registros_esperados = set(fechas_esperadas)

    df_ventas_validar = df_ventas[
        df_ventas["farmacia"].isin(farmacias_validar)
    ].copy()

    registros_existentes = set(
        zip(
            df_ventas_validar["farmacia"],
            df_ventas_validar["fecha"].dt.date
        )
    )

    faltantes = registros_esperados - registros_existentes

    df_faltantes = pd.DataFrame(
        sorted(faltantes),
        columns=["Farmacia", "Fecha"]
    )

    if not df_faltantes.empty:
        df_faltantes["Fecha"] = pd.to_datetime(
            df_faltantes["Fecha"]
        ).dt.strftime("%d/%m/%Y")

    return df_faltantes




# ==================================================
# CATÁLOGOS Y FILTROS
# ==================================================

df_farmacias, df_anios = cargar_catalogos(conn)

hoy = datetime.today()
anio_actual = hoy.year
mes_actual = hoy.month

st.sidebar.header("Filtros")

farmacias_opciones = ["Todas"] + df_farmacias["nombre"].dropna().tolist()

farmacia_sel = st.sidebar.selectbox(
    "Farmacia",
    farmacias_opciones,
    key="dashboard_filtro_farmacia"
)

anios_disponibles = df_anios["anio"].dropna().astype(int).tolist()

if not anios_disponibles:
    anios_disponibles = [anio_actual]

anios_opciones = ["Todos"] + anios_disponibles

index_anio = (
    anios_opciones.index(anio_actual)
    if anio_actual in anios_opciones
    else 0
)

anio_sel = st.sidebar.selectbox(
    "Año",
    anios_opciones,
    index=index_anio,
    key="dashboard_filtro_anio"
)

meses_disponibles = cargar_meses_disponibles(
    conn,
    anio_sel
)

meses_opciones = ["Todos"] + [
    f"{mes} - {MESES_ES[mes]}"
    for mes in meses_disponibles
]

mes_actual_label = f"{mes_actual} - {MESES_ES[mes_actual]}"

index_mes = (
    meses_opciones.index(mes_actual_label)
    if mes_actual_label in meses_opciones
    else 0
)

mes_sel = st.sidebar.selectbox(
    "Mes",
    meses_opciones,
    index=index_mes,
    key="dashboard_filtro_mes"
)

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.success(
    f"{st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button(
    "Cerrar sesión",
    key="btn_cerrar_sesion_dashboard"
):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")


# ==================================================
# CARGA DE DATOS FILTRADOS
# ==================================================

fecha_inicio, fecha_fin = obtener_fechas_periodo(
    anio_sel,
    mes_sel
)

df_ventas = cargar_ventas(
    conn,
    farmacia_sel,
    fecha_inicio,
    fecha_fin
)

df_gastos = cargar_gastos(
    conn,
    farmacia_sel,
    fecha_inicio,
    fecha_fin
)

periodo_kpi = obtener_etiqueta_periodo(
    anio_sel,
    mes_sel,
    farmacia_sel
)

fecha_inicio_ant, fecha_fin_ant, etiqueta_periodo_anterior = obtener_periodo_anterior(
    anio_sel,
    mes_sel
)

df_ventas_ant = pd.DataFrame()
df_gastos_ant = pd.DataFrame()

if fecha_inicio_ant is not None and fecha_fin_ant is not None:
    df_ventas_ant = cargar_ventas(
        conn,
        farmacia_sel,
        fecha_inicio_ant,
        fecha_fin_ant
    )

    df_gastos_ant = cargar_gastos(
        conn,
        farmacia_sel,
        fecha_inicio_ant,
        fecha_fin_ant
    )

try:
    conn.close()
except Exception:
    pass


# ==================================================
# ENCABEZADO
# ==================================================

st.title("Dashboard Financiero")
st.caption(f"Periodo analizado: {periodo_kpi}")

if df_ventas.empty and df_gastos.empty:
    st.warning("No hay datos para el periodo seleccionado.")
    st.info(
        "No existen registros de ventas ni gastos en este rango. "
        "Selecciona otro mes, año o farmacia en los filtros laterales."
    )
    st.stop()


# ==================================================
# 1. RESUMEN EJECUTIVO
# ==================================================

ventas_total = df_ventas["ventas_totales"].sum()
gastos_total = df_gastos["monto"].sum()
utilidad = ventas_total - gastos_total
margen = (utilidad / ventas_total * 100) if ventas_total > 0 else 0

ventas_ant = (
    df_ventas_ant["ventas_totales"].sum()
    if not df_ventas_ant.empty
    else 0
)

gastos_ant = (
    df_gastos_ant["monto"].sum()
    if not df_gastos_ant.empty
    else 0
)

utilidad_ant = ventas_ant - gastos_ant

margen_ant = (
    utilidad_ant / ventas_ant * 100
    if ventas_ant > 0
    else 0
)

st.subheader("Resumen ejecutivo")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Ventas totales",
        formato_moneda(ventas_total),
        texto_delta(ventas_total, ventas_ant)
    )

with col2:
    st.metric(
        "Gastos totales",
        formato_moneda(gastos_total),
        texto_delta(gastos_total, gastos_ant),
        delta_color="inverse"
    )

with col3:
    st.metric(
        "Utilidad operativa",
        formato_moneda(utilidad),
        texto_delta(utilidad, utilidad_ant)
    )

with col4:
    st.metric(
        "Margen",
        formato_porcentaje(margen),
        texto_delta(margen, margen_ant)
    )

if etiqueta_periodo_anterior:
    st.caption(f"Comparativo contra: {etiqueta_periodo_anterior}")
else:
    st.caption("Selecciona un año o mes específico para ver comparación contra periodo anterior.")

st.divider()


# ==================================================
# 2. CALIDAD DE DATOS
# ==================================================

st.subheader("Calidad de datos")

df_faltantes = validar_registros_faltantes(
    df_ventas,
    df_farmacias,
    farmacia_sel,
    anio_sel,
    mes_sel
)

if df_faltantes is None:
    st.info(
        "Selecciona un año y mes específico para validar registros faltantes. "
        "La validación espera un registro diario de ventas por farmacia activa."
    )

elif df_faltantes.empty:
    st.success("Todos los registros diarios de ventas del periodo están completos.")

else:
    st.warning(
        f"Mes incompleto. Faltan {len(df_faltantes)} registros diarios de ventas por capturar."
    )

    with st.expander("Ver registros faltantes", expanded=False):
        st.dataframe(
            df_faltantes,
            use_container_width=True,
            hide_index=True
        )

st.divider()


# ==================================================
# 3. TENDENCIA Y PROYECCIÓN
# ==================================================

st.subheader("Tendencia y proyección")

tipo_visualizacion = st.selectbox(
    "Visualización de tendencia",
    [
        "Diaria",
        "Semanal",
        "Mensual"
    ],
    key="dashboard_tipo_tendencia"
)

df_tendencia_base = df_ventas.copy()

if df_tendencia_base.empty:
    st.info("No hay ventas para mostrar tendencia.")

else:

    if tipo_visualizacion == "Diaria":

        df_tendencia_base["semana_mes"] = (
            (df_tendencia_base["fecha"].dt.day - 1) // 7
        ) + 1

        semanas = sorted(
            df_tendencia_base["semana_mes"].dropna().unique().tolist()
        )

        opciones_semana = ["Todas"] + semanas

        semana_sel = st.selectbox(
            "Semana del mes",
            opciones_semana,
            key="dashboard_semana_tendencia"
        )

        if semana_sel != "Todas":
            df_tendencia_base = df_tendencia_base[
                df_tendencia_base["semana_mes"] == semana_sel
            ]

        df_tendencia = (
            df_tendencia_base
            .groupby(df_tendencia_base["fecha"].dt.date)["ventas_totales"]
            .sum()
            .reset_index()
        )

        df_tendencia["Etiqueta"] = pd.to_datetime(
            df_tendencia["fecha"]
        ).dt.strftime("%d/%m/%Y")

        titulo_tendencia = "Tendencia diaria de ventas"

    elif tipo_visualizacion == "Semanal":

        df_tendencia = (
            df_tendencia_base
            .groupby(df_tendencia_base["fecha"].dt.to_period("W"))["ventas_totales"]
            .sum()
            .reset_index()
        )

        df_tendencia["inicio"] = df_tendencia["fecha"].apply(
            lambda x: x.start_time
        )

        df_tendencia["Etiqueta"] = (
            "Semana " +
            df_tendencia["inicio"].dt.isocalendar().week.astype(str) +
            " - " +
            df_tendencia["inicio"].dt.strftime("%d/%m/%Y")
        )

        titulo_tendencia = "Tendencia semanal de ventas"

    else:

        df_tendencia = (
            df_tendencia_base
            .groupby(df_tendencia_base["fecha"].dt.to_period("M"))["ventas_totales"]
            .sum()
            .reset_index()
        )

        df_tendencia["Etiqueta"] = (
            df_tendencia["fecha"].dt.strftime("%B").map(MESES_ES)
            + " "
            + df_tendencia["fecha"].dt.strftime("%Y")
        )

        titulo_tendencia = "Tendencia mensual de ventas"

    if df_tendencia.empty:
        st.info("No hay datos suficientes para la visualización seleccionada.")

    else:
        fig_tendencia = px.line(
            df_tendencia,
            x="Etiqueta",
            y="ventas_totales",
            markers=True,
            title=titulo_tendencia
        )

        fig_tendencia.update_traces(
            hovertemplate="<b>%{x}</b><br>Ventas: $%{y:,.2f}<extra></extra>"
        )

        st.plotly_chart(
            fig_tendencia,
            use_container_width=True
        )

# -------------------------------
# PROYECCIÓN
# -------------------------------

col1, col2 = st.columns([2, 1])

with col1:

    st.markdown("### Proyección de ventas")

    puede_proyectar = (
        anio_sel != "Todos"
        and mes_sel != "Todos"
        and int(anio_sel) == hoy.year
        and int(str(mes_sel).split(" - ")[0]) == hoy.month
        and not df_ventas.empty
    )

    if not puede_proyectar:

        st.info(
            "La proyección se calcula solamente para el mes actual, "
            "con año y mes específicos seleccionados."
        )

    else:

        mes_num = int(str(mes_sel).split(" - ")[0])
        dias_mes = monthrange(int(anio_sel), mes_num)[1]

        ventas_diarias_farmacia = (
            df_ventas
            .groupby(["farmacia", df_ventas["fecha"].dt.date])["ventas_totales"]
            .sum()
            .reset_index()
        )

        proyeccion_restante = 0

        for farmacia, df_farma in ventas_diarias_farmacia.groupby("farmacia"):

            promedio_diario_farmacia = df_farma["ventas_totales"].mean()
            ultimo_dia_farmacia = pd.to_datetime(
                df_farma["fecha"]
            ).max().day

            dias_restantes_farmacia = max(
                0,
                dias_mes - ultimo_dia_farmacia
            )

            proyeccion_restante += (
                promedio_diario_farmacia *
                dias_restantes_farmacia
            )

        ventas_proyectadas = ventas_total + proyeccion_restante

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Ventas actuales",
            formato_moneda(ventas_total)
        )

        c2.metric(
            "Proyección restante",
            formato_moneda(proyeccion_restante)
        )

        c3.metric(
            "Proyección fin de mes",
            formato_moneda(ventas_proyectadas)
        )

        st.caption(
            "Proyección calculada por farmacia con base en su promedio diario "
            "y los días restantes del mes."
        )

with col2:

    with st.expander("Ver promedios", expanded=True):

        ventas_diarias = (
            df_ventas
            .groupby(df_ventas["fecha"].dt.date)["ventas_totales"]
            .sum()
        )

        ventas_semanales = (
            df_ventas
            .groupby(df_ventas["fecha"].dt.to_period("W"))["ventas_totales"]
            .sum()
        )

        ventas_mensuales = (
            df_ventas
            .groupby(df_ventas["fecha"].dt.to_period("M"))["ventas_totales"]
            .sum()
        )

        prom_diario = ventas_diarias.mean() if not ventas_diarias.empty else 0
        prom_semanal = ventas_semanales.mean() if not ventas_semanales.empty else 0
        prom_mensual = ventas_mensuales.mean() if not ventas_mensuales.empty else 0

        st.metric(
            "Promedio diario",
            formato_moneda(prom_diario)
        )

        st.metric(
            "Promedio semanal",
            formato_moneda(prom_semanal)
        )

        st.metric(
            "Promedio mensual",
            formato_moneda(prom_mensual)
        )

st.divider()


# ==================================================
# 4. RENDIMIENTO POR FARMACIA
# ==================================================

st.subheader("Rendimiento por farmacia")

df_rendimiento = crear_dataframe_rendimiento(
    df_ventas,
    df_gastos,
    df_farmacias
)

if df_rendimiento.empty:

    st.info("No hay datos suficientes para calcular rendimiento por farmacia.")

else:

    top_venta = df_rendimiento.sort_values(
        "ventas_totales",
        ascending=False
    ).iloc[0]

    top_utilidad = df_rendimiento.sort_values(
        "utilidad",
        ascending=False
    ).iloc[0]

    farmacias_utilidad_negativa = df_rendimiento[
        df_rendimiento["utilidad"] < 0
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Farmacia con mayor venta",
        top_venta["farmacia"],
        formato_moneda(top_venta["ventas_totales"])
    )

    col2.metric(
        "Farmacia con mayor utilidad",
        top_utilidad["farmacia"],
        formato_moneda(top_utilidad["utilidad"])
    )

    col3.metric(
        "Farmacias con utilidad negativa",
        len(farmacias_utilidad_negativa)
    )

    if not farmacias_utilidad_negativa.empty:
        with st.expander("Ver farmacias con utilidad negativa", expanded=False):
            df_negativas = farmacias_utilidad_negativa[
                [
                    "farmacia",
                    "ventas_totales",
                    "monto",
                    "utilidad",
                    "margen"
                ]
            ].copy()

            df_negativas = df_negativas.rename(columns={
                "farmacia": "Farmacia",
                "ventas_totales": "Ventas",
                "monto": "Gastos",
                "utilidad": "Utilidad",
                "margen": "Margen %"
            })

            st.dataframe(
                df_negativas,
                use_container_width=True,
                hide_index=True
            )

    st.markdown("### Tabla de rendimiento")

    df_tabla_rendimiento = df_rendimiento.copy()

    df_tabla_rendimiento["ventas_totales"] = df_tabla_rendimiento["ventas_totales"].map(
        formato_moneda
    )

    df_tabla_rendimiento["monto"] = df_tabla_rendimiento["monto"].map(
        formato_moneda
    )

    df_tabla_rendimiento["utilidad"] = df_tabla_rendimiento["utilidad"].map(
        formato_moneda
    )

    df_tabla_rendimiento["margen"] = df_tabla_rendimiento["margen"].map(
        formato_porcentaje
    )

    df_tabla_rendimiento = df_tabla_rendimiento.rename(columns={
        "farmacia": "Farmacia",
        "ventas_totales": "Ventas",
        "monto": "Gastos",
        "utilidad": "Utilidad",
        "margen": "Margen",
        "estado": "Estado"
    })

    st.dataframe(
        df_tabla_rendimiento[
            [
                "Farmacia",
                "Estado",
                "Ventas",
                "Gastos",
                "Utilidad",
                "Margen"
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

    col1, col2 = st.columns(2)

    with col1:

        fig_utilidad_farmacia = px.bar(
            df_rendimiento,
            x="farmacia",
            y="utilidad",
            title="Utilidad neta por farmacia"
        )

        st.plotly_chart(
            fig_utilidad_farmacia,
            use_container_width=True
        )

    with col2:

        df_comparativo = df_rendimiento[
            [
                "farmacia",
                "ventas_totales",
                "monto"
            ]
        ].melt(
            id_vars="farmacia",
            value_vars=[
                "ventas_totales",
                "monto"
            ],
            var_name="Concepto",
            value_name="Monto"
        )

        df_comparativo["Concepto"] = df_comparativo["Concepto"].replace({
            "ventas_totales": "Ventas",
            "monto": "Gastos"
        })

        fig_ventas_gastos = px.bar(
            df_comparativo,
            x="farmacia",
            y="Monto",
            color="Concepto",
            barmode="group",
            title="Ventas y gastos por farmacia"
        )

        st.plotly_chart(
            fig_ventas_gastos,
            use_container_width=True
        )

st.divider()


# ==================================================
# 5. ANÁLISIS DE GASTOS
# ==================================================

st.subheader("Análisis de gastos")

if df_gastos.empty:

    st.info("No hay gastos registrados para el periodo seleccionado.")

else:

    df_gastos_categoria = (
        df_gastos
        .assign(
            categoria=df_gastos["categoria"].fillna("Sin categoría")
        )
        .groupby("categoria", as_index=False)["monto"]
        .sum()
        .sort_values("monto", ascending=False)
    )

    df_gastos_categoria["porcentaje"] = (
        df_gastos_categoria["monto"] /
        df_gastos_categoria["monto"].sum() *
        100
    )

    col1, col2 = st.columns([1, 1])

    with col1:

        st.markdown("### Gastos por categoría")

        df_tabla_gastos_categoria = df_gastos_categoria.copy()

        df_tabla_gastos_categoria["monto"] = df_tabla_gastos_categoria["monto"].map(
            formato_moneda
        )

        df_tabla_gastos_categoria["porcentaje"] = df_tabla_gastos_categoria["porcentaje"].map(
            formato_porcentaje
        )

        df_tabla_gastos_categoria = df_tabla_gastos_categoria.rename(columns={
            "categoria": "Categoría",
            "monto": "Monto",
            "porcentaje": "% del gasto"
        })

        st.dataframe(
            df_tabla_gastos_categoria,
            use_container_width=True,
            hide_index=True
        )

    with col2:

        fig_gastos_categoria = px.bar(
            df_gastos_categoria,
            x="categoria",
            y="monto",
            title="Distribución de gastos por categoría"
        )

        st.plotly_chart(
            fig_gastos_categoria,
            use_container_width=True
        )

st.divider()


# ==================================================
# 6. REPORTE
# ==================================================

st.subheader("Reporte")

if st.button(
    "Generar reporte PDF",
    key="dashboard_generar_reporte_pdf"
):
    pdf = generar_reporte_financiero(
        df_ventas,
        df_gastos,
        periodo_kpi
    )

    st.download_button(
        "Descargar reporte",
        pdf,
        file_name=f"reporte_financiero_{periodo_kpi.replace(' ', '_')}.pdf",
        mime="application/pdf",
        key="dashboard_descargar_reporte_pdf"
    )
