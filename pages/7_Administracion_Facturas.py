import streamlit as st
import pandas as pd

from utils.conexionASupabase import get_connection
from utils.logger import registrar_log

# ===============================
# SEGURIDAD
# ===============================
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

if st.session_state["usuario"]["rol"] != "admin":
    st.error("No tienes permisos para esta sección")
    st.stop()

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

    # ---------------------------------
# NUEVO PROVEEDOR
# ---------------------------------

    st.subheader("Registrar proveedor")

    with st.form("form_nuevo_proveedor", clear_on_submit=True):

        nombre = st.text_input("Nombre del proveedor")

        col1, col2 = st.columns(2)

        with col1:
            contacto = st.text_input("Contacto")

            telefono = st.text_input("Teléfono")

        with col2:
            correo = st.text_input("Correo")

            dias_credito = st.number_input(
                "Días de crédito",
                min_value=0,
                max_value=365,
                value=30
            )

        observaciones = st.text_area(
            "Observaciones",
            height=80
        )

        guardar = st.form_submit_button("Guardar proveedor")

    if guardar:

        if nombre.strip() == "":
            st.error("El nombre del proveedor es obligatorio.")
            st.stop()

        cursor.execute("""
            SELECT COUNT(*)
            FROM proveedores
            WHERE UPPER(nombre)=UPPER(%s)
        """, (nombre.strip(),))

        existe = cursor.fetchone()[0]

        if existe > 0:

            st.warning("Ya existe un proveedor con ese nombre.")

        else:

            try:

                cursor.execute("""

                    INSERT INTO proveedores
                    (
                        nombre,
                        contacto,
                        telefono,
                        correo,
                        dias_credito,
                        estado,
                        observaciones
                    )

                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        'ACTIVO',
                        %s
                    )

                """,

                (
                    nombre.strip(),
                    contacto.strip(),
                    telefono.strip(),
                    correo.strip(),
                    dias_credito,
                    observaciones.strip()
                ))

                conn.commit()

                registrar_log(
                    st.session_state["usuario"],
                    "ALTA_PROVEEDOR",
                    f"Registró el proveedor {nombre}"
                )

                st.success("Proveedor registrado correctamente.")

                st.rerun()

            except Exception as e:

                conn.rollback()

                st.error(e)
        st.divider()

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
