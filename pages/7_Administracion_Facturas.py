import streamlit as st
import pandas as pd

from datetime import timedelta
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


#----------------------------
#GESTION DE PROVEEDORES
#----------------------------




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

    st.subheader("Editar proveedor")

    if not df_proveedores.empty:

        opciones = {
            fila["nombre"]: fila["proveedor_id"]
            for _, fila in df_proveedores.iterrows()
        }

        proveedor_sel = st.selectbox(
            "Proveedor",
            list(opciones.keys())
        )

        proveedor_id = opciones[proveedor_sel]

        cursor.execute("""
            SELECT
                nombre,
                contacto,
                telefono,
                correo,
                dias_credito,
                estado,
                observaciones
            FROM proveedores
            WHERE proveedor_id=%s
        """,(proveedor_id,))

        datos = cursor.fetchone()
        nombre_edit = st.text_input(
        "Nombre",
        value=datos[0]
        )

    col1,col2 = st.columns(2)

    with col1:

        contacto_edit = st.text_input(
            "Contacto",
            value=datos[1] or ""
        )

        telefono_edit = st.text_input(
            "Teléfono",
            value=datos[2] or ""
        )

    with col2:

        correo_edit = st.text_input(
            "Correo",
            value=datos[3] or ""
        )

        dias_edit = st.number_input(
            "Días de crédito",
            min_value=0,
            max_value=365,
            value=datos[4]
        )

    estado_edit = st.selectbox(
        "Estado",
        ["ACTIVO","CERRADA"],
        index=0 if datos[5]=="ACTIVO" else 1
    )

    observaciones_edit = st.text_area(
        "Observaciones",
        value=datos[6] or ""
    )

    col1,col2 = st.columns(2)
    with col1:

        if st.button("Guardar cambios"):

            try:

                cursor.execute("""

                UPDATE proveedores

                SET

                    nombre=%s,

                    contacto=%s,

                    telefono=%s,

                    correo=%s,

                    dias_credito=%s,

                    estado=%s,

                    observaciones=%s

                WHERE proveedor_id=%s

                """,

                (

                    nombre_edit,

                    contacto_edit,

                    telefono_edit,

                    correo_edit,

                    dias_edit,

                    estado_edit,

                    observaciones_edit,

                    proveedor_id

                ))

                conn.commit()

                registrar_log(

                    st.session_state["usuario"],

                    "MODIFICACION_PROVEEDOR",

                    f"Modificó proveedor {nombre_edit}"

                )

                st.success("Proveedor actualizado correctamente.")

                st.rerun()

            except Exception as e:

                conn.rollback()

                st.error(e)
    with col2:

        if estado_edit=="ACTIVO":

            st.success("Proveedor activo")

        else:

            st.warning("Proveedor cerrado")

    st.divider()


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

with tab2:

    st.subheader("Registrar factura")

    df_proveedores = pd.read_sql("""
        SELECT
            proveedor_id,
            nombre,
            dias_credito
        FROM proveedores
        WHERE estado='ACTIVO'
        ORDER BY nombre
    """, conn)

    if df_proveedores.empty:
        st.warning("No existen proveedores activos.")
        st.stop()
    with st.form("form_factura", clear_on_submit=True):

        proveedor = st.selectbox(
            "Proveedor",
            df_proveedores["nombre"]
        )

        col1, col2 = st.columns(2)

        with col1:

            folio = st.text_input("Folio")

            fecha_factura = st.date_input(
                "Fecha de factura"
            )

        with col2:

            monto = st.number_input(
                "Monto",
                min_value=0.0,
                step=100.0,
                format="%.2f"
            )

            estatus = st.selectbox(
                "Estatus",
                [
                    "PENDIENTE",
                    "PAGADA"
                ]
            )

        observaciones = st.text_area(
            "Observaciones"
        )

        guardar = st.form_submit_button(
            "Guardar factura"
        )
    if guardar:

        proveedor_id = int(
            df_proveedores.loc[
                df_proveedores["nombre"] == proveedor,
                "proveedor_id"
            ].iloc[0]
        )

        dias_credito = int(
            df_proveedores.loc[
                df_proveedores["nombre"] == proveedor,
                "dias_credito"
            ].iloc[0]
        )
        fecha_vencimiento = (
        fecha_factura +
        timedelta(days=dias_credito)
        )
    cursor.execute("""

    SELECT COUNT(*)

    FROM facturas

    WHERE folio=%s
    AND proveedor_id=%s

    """,

    (
        folio.strip(),
        proveedor_id
    ))

    if cursor.fetchone()[0] > 0:

        st.error(
            "Ya existe ese folio para este proveedor."
        )

        st.stop()
    try:

        cursor.execute("""

            INSERT INTO facturas
            (
                proveedor_id,
                folio,
                fecha_factura,
                fecha_vencimiento,
                monto,
                estatus,
                observaciones
            )

            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )

        """,

        (
            proveedor_id,
            folio.strip(),
            fecha_factura,
            fecha_vencimiento,
            monto,
            estatus,
            observaciones.strip()
        ))

        conn.commit()
        registrar_log(

        st.session_state["usuario"],

        "ALTA_FACTURA",

        f"Registró la factura {folio} del proveedor {proveedor}"
        )   
    
        st.success("Factura registrada correctamente.")
        st.rerun()
    except Exception as e:

        conn.rollback()

        st.error(e)

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
