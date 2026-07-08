import streamlit as st
import pandas as pd
from datetime import date, timedelta
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



tab1, tab2, tab3, tab4 = st.tabs([
    "Facturas",
    "Agregar Factura",
    "Proveedores",
    "Estadísticas"
])

# ----------------------------
# GESTIÓN DE FACTURAS
# ----------------------------

with tab1:

    st.subheader("Panel de facturas")

    df_facturas = pd.read_sql("""
        SELECT
            f.factura_id,
            p.nombre AS proveedor,
            f.folio,
            f.fecha_factura,
            f.dias_credito,
            f.fecha_vencimiento,
            f.monto,
            f.estatus,
            f.observaciones
        FROM facturas f
        LEFT JOIN proveedores p
            ON f.proveedor_id = p.proveedor_id
        ORDER BY
            f.fecha_vencimiento ASC,
            f.created_at DESC
    """, conn)

    if df_facturas.empty:

        st.info("Todavía no hay facturas registradas.")

    else:

        # ----------------------------
        # LIMPIEZA DE FECHAS
        # ----------------------------

        df_facturas["fecha_factura"] = pd.to_datetime(
            df_facturas["fecha_factura"]
        ).dt.date

        df_facturas["fecha_vencimiento"] = pd.to_datetime(
            df_facturas["fecha_vencimiento"]
        ).dt.date

        hoy = date.today()

        df_facturas["dias_restantes"] = df_facturas["fecha_vencimiento"].apply(
            lambda fecha: (fecha - hoy).days if pd.notnull(fecha) else None
        )

        # ----------------------------
        # CLASIFICACIÓN DE URGENCIA
        # ----------------------------

        def clasificar_urgencia(fila):

            if fila["estatus"] == "PAGADA":
                return "PAGADA"

            if fila["estatus"] == "CANCELADA":
                return "CANCELADA"

            dias = fila["dias_restantes"]

            if dias < 0:
                return "VENCIDA"

            if dias <= 3:
                return "URGENTE"

            if dias <= 7:
                return "PRÓXIMA"

            return "EN TIEMPO"

        df_facturas["urgencia"] = df_facturas.apply(
            clasificar_urgencia,
            axis=1
        )

        # ----------------------------
        # FILTROS
        # ----------------------------

        st.markdown("### Filtros")

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            proveedores = ["Todos"] + sorted(
                df_facturas["proveedor"].dropna().unique().tolist()
            )

            filtro_proveedor = st.selectbox(
                "Proveedor",
                proveedores
            )

        with col2:

            filtro_estatus = st.selectbox(
                "Estatus",
                [
                    "Todos",
                    "PENDIENTE",
                    "PAGADA",
                    "CANCELADA"
                ]
            )

        with col3:

            filtro_vencimiento = st.selectbox(
                "Vencimiento",
                [
                    "Todos",
                    "Vencidas",
                    "Vencen en 7 días",
                    "En tiempo"
                ]
            )

        with col4:

            buscar_folio = st.text_input(
                "Buscar folio",
                placeholder="Ej. F12345"
            )

        df_filtrado = df_facturas.copy()

        if filtro_proveedor != "Todos":

            df_filtrado = df_filtrado[
                df_filtrado["proveedor"] == filtro_proveedor
            ]

        if filtro_estatus != "Todos":

            df_filtrado = df_filtrado[
                df_filtrado["estatus"] == filtro_estatus
            ]

        if filtro_vencimiento == "Vencidas":

            df_filtrado = df_filtrado[
                (df_filtrado["estatus"] == "PENDIENTE") &
                (df_filtrado["dias_restantes"] < 0)
            ]

        elif filtro_vencimiento == "Vencen en 7 días":

            df_filtrado = df_filtrado[
                (df_filtrado["estatus"] == "PENDIENTE") &
                (df_filtrado["dias_restantes"] >= 0) &
                (df_filtrado["dias_restantes"] <= 7)
            ]

        elif filtro_vencimiento == "En tiempo":

            df_filtrado = df_filtrado[
                (df_filtrado["estatus"] == "PENDIENTE") &
                (df_filtrado["dias_restantes"] > 7)
            ]

        if buscar_folio.strip():

            df_filtrado = df_filtrado[
                df_filtrado["folio"]
                .astype(str)
                .str.contains(buscar_folio.strip(), case=False, na=False)
            ]

        # ----------------------------
        # KPIS
        # ----------------------------

        pendientes = df_filtrado[
            df_filtrado["estatus"] == "PENDIENTE"
        ]

        vencidas = df_filtrado[
            (df_filtrado["estatus"] == "PENDIENTE") &
            (df_filtrado["dias_restantes"] < 0)
        ]

        proximas = df_filtrado[
            (df_filtrado["estatus"] == "PENDIENTE") &
            (df_filtrado["dias_restantes"] >= 0) &
            (df_filtrado["dias_restantes"] <= 7)
        ]

        pagadas = df_filtrado[
            df_filtrado["estatus"] == "PAGADA"
        ]

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "Pendiente por pagar",
                f"${pendientes['monto'].sum():,.2f}"
            )

        with col2:

            st.metric(
                "Facturas pendientes",
                len(pendientes)
            )

        with col3:

            st.metric(
                "Facturas vencidas",
                len(vencidas)
            )

        with col4:

            st.metric(
                "Vencen en 7 días",
                len(proximas)
            )

        st.divider()

        # ----------------------------
        # TABLA DE FACTURAS
        # ----------------------------

        st.markdown("### Facturas registradas")

        df_mostrar = df_filtrado[[
            "factura_id",
            "proveedor",
            "folio",
            "fecha_factura",
            "dias_credito",
            "fecha_vencimiento",
            "dias_restantes",
            "monto",
            "estatus",
            "urgencia",
            "observaciones"
        ]].copy()

        df_mostrar = df_mostrar.rename(columns={
            "factura_id": "ID",
            "proveedor": "Proveedor",
            "folio": "Folio",
            "fecha_factura": "Fecha factura",
            "dias_credito": "Días crédito",
            "fecha_vencimiento": "Fecha vencimiento",
            "dias_restantes": "Días restantes",
            "monto": "Monto",
            "estatus": "Estatus",
            "urgencia": "Urgencia",
            "observaciones": "Observaciones"
        })

        def colorear_filas(fila):

            if fila["Urgencia"] == "VENCIDA":
                return ["background-color: #f4cccc"] * len(fila)

            if fila["Urgencia"] == "URGENTE":
                return ["background-color: #fff2cc"] * len(fila)

            if fila["Urgencia"] == "PRÓXIMA":
                return ["background-color: #d9ead3"] * len(fila)

            return [""] * len(fila)

        st.dataframe(
            df_mostrar.style.apply(
                colorear_filas,
                axis=1
            ),
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            f"Facturas mostradas: {len(df_filtrado)}"
        )

        st.divider()

        # ----------------------------
        # ACCIONES SOBRE FACTURAS
        # ----------------------------

        st.markdown("### Actualizar estatus de factura")

        df_acciones = df_facturas[
            df_facturas["estatus"] == "PENDIENTE"
        ].copy()

        if df_acciones.empty:

            st.info("No hay facturas pendientes para actualizar.")

        else:

            opciones_facturas = {}

            for _, fila in df_acciones.iterrows():

                etiqueta = (
                    f"{fila['proveedor']} | "
                    f"Folio: {fila['folio']} | "
                    f"Vence: {fila['fecha_vencimiento']} | "
                    f"${float(fila['monto']):,.2f}"
                )

                opciones_facturas[etiqueta] = int(fila["factura_id"])

            factura_sel = st.selectbox(
                "Selecciona una factura pendiente",
                list(opciones_facturas.keys())
            )

            factura_id_sel = opciones_facturas[factura_sel]

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "Marcar como pagada",
                    use_container_width=True
                ):

                    try:

                        cursor.execute("""
                            UPDATE facturas
                            SET estatus = 'PAGADA'
                            WHERE factura_id = %s
                        """, (
                            factura_id_sel,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "FACTURA_PAGADA",
                            f"Marcó como pagada la factura ID {factura_id_sel}"
                        )

                        st.success("Factura marcada como pagada correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)

            with col2:

                if st.button(
                    "Cancelar factura",
                    use_container_width=True
                ):

                    try:

                        cursor.execute("""
                            UPDATE facturas
                            SET estatus = 'CANCELADA'
                            WHERE factura_id = %s
                        """, (
                            factura_id_sel,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "FACTURA_CANCELADA",
                            f"Canceló la factura ID {factura_id_sel}"
                        )

                        st.success("Factura cancelada correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)

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

    df_proveedores_activos = pd.read_sql("""
        SELECT
            proveedor_id,
            nombre,
            dias_credito
        FROM proveedores
        WHERE estado = 'ACTIVO'
        ORDER BY nombre
    """, conn)

    if df_proveedores_activos.empty:

        st.warning("No existen proveedores activos para registrar facturas.")

    else:

        proveedores_nombres = df_proveedores_activos["nombre"].tolist()

        with st.form("form_registrar_factura", clear_on_submit=True):

            proveedor = st.selectbox(
                "Proveedor",
                proveedores_nombres
            )

            proveedor_row = df_proveedores_activos[
                df_proveedores_activos["nombre"] == proveedor
            ].iloc[0]

            proveedor_id = int(proveedor_row["proveedor_id"])
            dias_credito_default = int(proveedor_row["dias_credito"])

            col1, col2 = st.columns(2)

            with col1:

                folio = st.text_input(
                    "Folio de factura"
                )

                fecha_factura = st.date_input(
                    "Fecha de factura",
                    value=date.today()
                )

                dias_credito = st.number_input(
                    "Días de crédito",
                    min_value=0,
                    max_value=365,
                    value=dias_credito_default
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
                    ["PENDIENTE", "PAGADA", "CANCELADA"]
                )

                fecha_vencimiento = fecha_factura + timedelta(
                    days=int(dias_credito)
                )

                st.info(
                    f"Fecha de vencimiento calculada: {fecha_vencimiento.strftime('%d/%m/%Y')}"
                )

            observaciones = st.text_area(
                "Observaciones"
            )

            guardar = st.form_submit_button(
                "Guardar factura"
            )

        if guardar:

            if folio.strip() == "":

                st.error("El folio de la factura es obligatorio.")
                st.stop()

            if monto <= 0:

                st.error("El monto debe ser mayor a 0.")
                st.stop()

            cursor.execute("""
                SELECT COUNT(*)
                FROM facturas
                WHERE proveedor_id = %s
                AND UPPER(folio) = UPPER(%s)
            """, (
                proveedor_id,
                folio.strip()
            ))

            existe = cursor.fetchone()[0]

            if existe > 0:

                st.error("Ya existe una factura con ese folio para este proveedor.")
                st.stop()

            try:

                cursor.execute("""
                    INSERT INTO facturas
                    (
                        proveedor_id,
                        folio,
                        fecha_factura,
                        dias_credito,
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
                        %s,
                        %s
                    )
                """, (
                    proveedor_id,
                    folio.strip(),
                    fecha_factura,
                    int(dias_credito),
                    fecha_vencimiento,
                    monto,
                    estatus,
                    observaciones.strip()
                ))

                conn.commit()

                registrar_log(
                    st.session_state["usuario"],
                    "ALTA_FACTURA",
                    f"Registró la factura {folio.strip()} del proveedor {proveedor}"
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
