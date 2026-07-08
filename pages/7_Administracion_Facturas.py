import streamlit as st
import pandas as pd

from utils.conexionASupabase import get_connection
from utils.logger import registrar_log

st.set_page_config(
    page_title="Administración Facturas",
    layout="wide"
)

st.title("🧾 Administración de Facturas")


conn=get_connection()
cursor=conn.cursor()



if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")



tab1,tab2,tab3,tab4 = st.tabs([

"📋 Facturas",

"➕ Agregar Factura",

"🏭 Proveedores",


"📊 Estadísticas"

])
with tab3:

    st.subheader("Gestión de Proveedores")

    # ----------------------------
    # FILTROS
    # ----------------------------

    col1, col2 = st.columns([3,1])

    with col1:
        buscar = st.text_input(
            "Buscar proveedor",
            placeholder="Escribe el nombre del proveedor..."
        )

    with col2:
        mostrar_inactivos = st.checkbox(
            "Mostrar inactivos",
            value=False
        )

    # ----------------------------
    # CONSULTA
    # ----------------------------

    query = """
        SELECT
            proveedor_id,
            nombre,
            contacto,
            telefono,
            correo,
            dias_credito,
            estado,
            observaciones
        FROM proveedores
    """

    condiciones = []

    if not mostrar_inactivos:
        condiciones.append("estado='ACTIVO'")

    if buscar.strip():
        condiciones.append(
            f"UPPER(nombre) LIKE UPPER('%{buscar}%')"
        )

    if condiciones:
        query += " WHERE " + " AND ".join(condiciones)

    query += " ORDER BY nombre"

    df_proveedores = pd.read_sql(query, conn)

    # ----------------------------
    # TABLA
    # ----------------------------

    if df_proveedores.empty:

        st.info("No hay proveedores para mostrar.")

    else:

        st.dataframe(
            df_proveedores,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            f"Total proveedores: {len(df_proveedores)}"
        )
    st.divider()