import streamlit as st
import pandas as pd

from utils.conexionASupabase import get_connection
from utils.logger import registrar_log


st.set_page_config(
    page_title="Configuración",
    layout="wide"
)

# ===============================
# SEGURIDAD
# ===============================

if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

rol_usuario = st.session_state["usuario"]["rol"].strip().lower()

roles_permitidos = ["admin"]

if rol_usuario not in roles_permitidos:
    st.error("No tienes permisos para esta sección")
    st.stop()


# ===============================
# CONEXIÓN
# ===============================

conn = get_connection()
cursor = conn.cursor()


# ===============================
# INTERFAZ
# ===============================

st.title("Configuración")

tab1, tab2, tab3 = st.tabs([
    "Gestión de usuarios",
    "Gestión de farmacias",
    "Logs"
])


# ==================================================
# TAB 1 - GESTIÓN DE USUARIOS
# ==================================================

# ==================================================
# TAB 3 - LOGS
# ==================================================

with tab3:

    st.subheader("Logs del sistema")

    # ===============================
    # CARGA DE DATOS
    # ===============================

    df_logs = pd.read_sql("""
        SELECT
            log_id,
            usuario_nombre,
            accion,
            descripcion,
            fecha
        FROM logs_auditoria
        ORDER BY fecha DESC;
    """, conn)

    if df_logs.empty:

        st.info("Todavía no hay logs registrados en el sistema.")

    else:

        df_logs["fecha"] = pd.to_datetime(
            df_logs["fecha"],
            errors="coerce"
        )

        # ===============================
        # RESUMEN RÁPIDO
        # ===============================

        st.markdown("### Resumen rápido")

        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Total de logs",
                len(df_logs)
            )

        with col2:

            st.metric(
                "Usuarios únicos",
                df_logs["usuario_nombre"].nunique()
            )

        with col3:

            st.metric(
                "Acciones distintas",
                df_logs["accion"].nunique()
            )

        st.divider()

        # ===============================
        # FILTROS
        # ===============================

        st.markdown("### Filtros")

        usuarios = (
            ["Todos"] +
            sorted(df_logs["usuario_nombre"].dropna().unique().tolist())
        )

        acciones = (
            ["Todas"] +
            sorted(df_logs["accion"].dropna().unique().tolist())
        )

        anios = (
            ["Todos"] +
            sorted(df_logs["fecha"].dropna().dt.year.unique().tolist(), reverse=True)
        )

        meses = (
            ["Todos"] +
            sorted(df_logs["fecha"].dropna().dt.month.unique().tolist())
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            usuario_sel = st.selectbox(
                "Usuario",
                usuarios,
                key="config_logs_usuario"
            )

        with col2:

            accion_sel = st.selectbox(
                "Acción",
                acciones,
                key="config_logs_accion"
            )

        with col3:

            anio_sel = st.selectbox(
                "Año",
                anios,
                key="config_logs_anio"
            )

        with col4:

            mes_sel = st.selectbox(
                "Mes",
                meses,
                key="config_logs_mes"
            )

        col1, col2 = st.columns([3, 1])

        with col1:

            busqueda = st.text_input(
                "Buscar en descripción",
                placeholder="Ej. venta, gasto, proveedor, factura...",
                key="config_logs_busqueda"
            )

        with col2:

            page_size = st.selectbox(
                "Filas por página",
                [10, 25, 50, 100],
                index=1,
                key="config_logs_page_size"
            )

        # ===============================
        # APLICAR FILTROS
        # ===============================

        df_filt = df_logs.copy()

        if usuario_sel != "Todos":

            df_filt = df_filt[
                df_filt["usuario_nombre"] == usuario_sel
            ]

        if accion_sel != "Todas":

            df_filt = df_filt[
                df_filt["accion"] == accion_sel
            ]

        if anio_sel != "Todos":

            df_filt = df_filt[
                df_filt["fecha"].dt.year == int(anio_sel)
            ]

        if mes_sel != "Todos":

            df_filt = df_filt[
                df_filt["fecha"].dt.month == int(mes_sel)
            ]

        if busqueda.strip():

            df_filt = df_filt[
                df_filt["descripcion"]
                .astype(str)
                .str.contains(
                    busqueda.strip(),
                    case=False,
                    na=False
                )
            ]

        # ===============================
        # PAGINACIÓN
        # ===============================

        total = len(df_filt)

        total_pages = max(
            1,
            (total - 1) // int(page_size) + 1
        )

        if "config_logs_page" not in st.session_state:
            st.session_state["config_logs_page"] = 1

        if st.session_state["config_logs_page"] > total_pages:
            st.session_state["config_logs_page"] = 1

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:

            page = st.number_input(
                "Página",
                min_value=1,
                max_value=total_pages,
                value=st.session_state["config_logs_page"],
                step=1,
                key="config_logs_page"
            )

        with col2:

            st.metric(
                "Resultados",
                total
            )

        with col3:

            st.caption(
                f"Página {page} de {total_pages}. "
                f"Mostrando máximo {page_size} registros."
            )

        start = (int(page) - 1) * int(page_size)
        end = start + int(page_size)

        # ===============================
        # TABLA
        # ===============================

        st.markdown("### Registros de actividad")

        if df_filt.empty:

            st.info("No hay logs que coincidan con los filtros seleccionados.")

        else:

            df_mostrar = df_filt.iloc[start:end].copy()

            df_mostrar["fecha"] = df_mostrar["fecha"].dt.strftime(
                "%d/%m/%Y %H:%M"
            )

            df_mostrar = df_mostrar.rename(columns={
                "log_id": "ID",
                "usuario_nombre": "Usuario",
                "accion": "Acción",
                "descripcion": "Descripción",
                "fecha": "Fecha"
            })

            st.dataframe(
                df_mostrar,
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Mostrando {len(df_mostrar)} de {total} registros filtrados."
            )

# ==================================================
# TAB 2 - GESTIÓN DE FARMACIAS
# ==================================================

with tab2:

    st.subheader("Gestión de farmacias")

    st.info("Aquí integraremos la lógica de la página de Gestión de farmacias.")


# ==================================================
# TAB 3 - LOGS
# ==================================================

with tab3:

    st.subheader("Logs del sistema")

    st.info("Aquí integraremos la lógica de la página de Logs.")


# ===============================
# SIDEBAR INFO
# ===============================

st.sidebar.success(
    f"{st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button(
    "Cerrar sesión",
    key="btn_cerrar_sesion_configuracion"
):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")