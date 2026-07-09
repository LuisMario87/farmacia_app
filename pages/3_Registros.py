import streamlit as st
import pandas as pd
from datetime import date

from utils.conexionASupabase import get_connection
from utils.logger import registrar_log


st.set_page_config(
    page_title="Registros",
    layout="wide"
)

# ===============================
# SEGURIDAD
# ===============================

if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

rol_usuario = st.session_state["usuario"]["rol"].strip().lower()

roles_permitidos = ["admin", "empleado"]

if rol_usuario not in roles_permitidos:
    st.error("No tienes permisos para esta sección")
    st.stop()


# ===============================
# CONEXIÓN
# ===============================

conn = get_connection()
cursor = conn.cursor()


# ===============================
# DATOS BASE
# ===============================

cursor.execute("""
    SELECT
        farmacia_id,
        nombre
    FROM farmacias
    ORDER BY nombre;
""")

farmacias = cursor.fetchall()

if not farmacias:
    st.error("No hay farmacias registradas.")
    st.stop()

farmacia_dict = {
    f[1]: f[0]
    for f in farmacias
}

farmacia_reverse = {
    f[0]: f[1]
    for f in farmacias
}

farmacia_nombres = list(farmacia_dict.keys())


# ===============================
# FUNCIONES AUXILIARES
# ===============================

def venta_duplicada(cursor, farmacia_id, fecha):
    cursor.execute("""
        SELECT 1
        FROM ventas
        WHERE farmacia_id = %s
        AND fecha = %s
        LIMIT 1;
    """, (
        farmacia_id,
        fecha
    ))

    return cursor.fetchone() is not None


def folio_mercancia_duplicado(cursor, farmacia_id, folio):
    cursor.execute("""
        SELECT 1
        FROM gastos
        WHERE farmacia_id = %s
        AND categoria = 'Mercancia'
        AND folio = %s
        LIMIT 1;
    """, (
        farmacia_id,
        folio
    ))

    return cursor.fetchone() is not None


# ===============================
# INTERFAZ
# ===============================

st.title("Registros")

tab1, tab2 = st.tabs([
    "Registro de ventas",
    "Registro de gastos"
])


# ==================================================
# TAB 1 - REGISTRO DE VENTAS
# ==================================================

with tab1:

    st.subheader("Registro de ventas")

    # =================================
    # MODO DE REGISTRO
    # =================================

    modo = st.radio(
        "Modo de registro",
        [
            "Registro Individual",
            "Registro Rápido (Todas las farmacias)",
            "Registro Personalizado"
        ],
        key="ventas_modo_registro"
    )

    # =================================
    # DATOS COMUNES
    # =================================

    tipo_registro = st.selectbox(
        "Tipo de registro",
        ["diario"],
        key="ventas_tipo_registro"
    )

    fecha = st.date_input(
        "Fecha de la venta",
        value=date.today(),
        max_value=date.today(),
        key="ventas_fecha_registro"
    )

    st.divider()

    # =================================
    # REGISTRO INDIVIDUAL
    # =================================

    if modo == "Registro Individual":

        st.subheader("Registro Individual")

        farmacia_nombre = st.selectbox(
            "Farmacia",
            farmacia_nombres,
            key="ventas_farmacia_individual"
        )

        farmacia_id = farmacia_dict[farmacia_nombre]

        monto = st.number_input(
            "Monto de venta",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key="ventas_monto_individual"
        )

        venta_tarjeta = st.number_input(
            "Venta con tarjeta",
            min_value=0.0,
            step=100.0,
            format="%.2f",
            key="ventas_tarjeta_individual"
        )

        venta_efectivo = monto - venta_tarjeta

        st.info(
            f"Efectivo estimado: ${venta_efectivo:,.2f}"
        )

        if st.button(
            "Registrar venta",
            key="btn_registrar_venta_individual"
        ):

            if monto <= 0:
                st.error("El monto debe ser mayor a 0.")
                st.stop()

            if venta_tarjeta > monto:
                st.error("La venta con tarjeta no puede ser mayor a la venta total.")
                st.stop()

            if venta_duplicada(cursor, farmacia_id, fecha):
                st.error("Ya existe una venta registrada para esta farmacia en esa fecha.")
                st.stop()

            try:

                cursor.execute("""
                    INSERT INTO ventas
                    (
                        farmacia_id,
                        ventas_totales,
                        venta_tarjeta,
                        venta_efectivo,
                        tipo_registro,
                        fecha
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, (
                    farmacia_id,
                    monto,
                    venta_tarjeta,
                    venta_efectivo,
                    tipo_registro,
                    fecha
                ))

                conn.commit()

                registrar_log(
                    st.session_state["usuario"],
                    "REGISTRO_VENTA",
                    f"Registró una venta de ${monto:,.2f} en {farmacia_nombre} ({fecha})"
                )

                st.success("Venta registrada correctamente.")

                st.rerun()

            except Exception as e:

                conn.rollback()
                st.error(e)

    # =================================
    # REGISTRO RÁPIDO
    # =================================

    if modo == "Registro Rápido (Todas las farmacias)":

        st.subheader("Registro Rápido")

        registros = []

        for nombre, fid in farmacia_dict.items():

            col1, col2, col3 = st.columns(3)

            with col1:

                monto = st.number_input(
                    f"{nombre} - Venta total",
                    min_value=0.0,
                    step=500.0,
                    format="%.2f",
                    key=f"ventas_rapido_monto_{fid}"
                )

            with col2:

                tarjeta = st.number_input(
                    f"{nombre} - Tarjeta",
                    min_value=0.0,
                    step=100.0,
                    format="%.2f",
                    key=f"ventas_rapido_tarjeta_{fid}"
                )

            with col3:

                efectivo = monto - tarjeta

                st.metric(
                    "Efectivo",
                    f"${efectivo:,.2f}"
                )

            if tarjeta > monto:
                st.error(f"{nombre}: la venta con tarjeta no puede ser mayor a la venta total.")
                st.stop()

            if monto > 0:

                if venta_duplicada(cursor, fid, fecha):

                    st.warning(f"{nombre} ya tiene venta registrada ese día, se omitirá.")

                else:

                    registros.append((
                        fid,
                        monto,
                        tarjeta,
                        efectivo,
                        tipo_registro,
                        fecha
                    ))

        if st.button(
            "Registrar ventas",
            key="btn_registrar_ventas_rapidas"
        ):

            if not registros:
                st.warning("No hay montos válidos para registrar.")
                st.stop()

            try:

                cursor.executemany("""
                    INSERT INTO ventas
                    (
                        farmacia_id,
                        ventas_totales,
                        venta_tarjeta,
                        venta_efectivo,
                        tipo_registro,
                        fecha
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, registros)

                conn.commit()

                registrar_log(
                    st.session_state["usuario"],
                    "REGISTRO_VENTA",
                    f"Registró {len(registros)} ventas rápidas ({fecha})"
                )

                st.success(f"{len(registros)} ventas registradas correctamente.")

                st.rerun()

            except Exception as e:

                conn.rollback()
                st.error(e)

    # =================================
    # REGISTRO PERSONALIZADO
    # =================================

    if modo == "Registro Personalizado":

        st.subheader("Registro Personalizado")

        seleccionadas = st.multiselect(
            "Selecciona farmacias",
            farmacia_nombres,
            key="ventas_farmacias_personalizadas"
        )

        registros = []

        for nombre in seleccionadas:

            fid = farmacia_dict[nombre]

            col1, col2, col3 = st.columns(3)

            with col1:

                monto = st.number_input(
                    f"{nombre} - Venta total",
                    min_value=0.0,
                    step=500.0,
                    format="%.2f",
                    key=f"ventas_custom_monto_{fid}"
                )

            with col2:

                tarjeta = st.number_input(
                    f"{nombre} - Tarjeta",
                    min_value=0.0,
                    step=100.0,
                    format="%.2f",
                    key=f"ventas_custom_tarjeta_{fid}"
                )

            with col3:

                efectivo = monto - tarjeta

                st.metric(
                    "Efectivo",
                    f"${efectivo:,.2f}"
                )

            if tarjeta > monto:
                st.error(f"{nombre}: la venta con tarjeta no puede ser mayor a la venta total.")
                st.stop()

            if monto > 0:

                if venta_duplicada(cursor, fid, fecha):

                    st.warning(f"{nombre} ya tiene venta registrada ese día, se omitirá.")

                else:

                    registros.append((
                        fid,
                        monto,
                        tarjeta,
                        efectivo,
                        tipo_registro,
                        fecha
                    ))

        if st.button(
            "Registrar ventas seleccionadas",
            key="btn_registrar_ventas_personalizadas"
        ):

            if not registros:
                st.warning("No hay montos válidos para registrar.")
                st.stop()

            try:

                cursor.executemany("""
                    INSERT INTO ventas
                    (
                        farmacia_id,
                        ventas_totales,
                        venta_tarjeta,
                        venta_efectivo,
                        tipo_registro,
                        fecha
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    );
                """, registros)

                conn.commit()

                registrar_log(
                    st.session_state["usuario"],
                    "REGISTRO_VENTA",
                    f"Registró {len(registros)} ventas personalizadas ({fecha})"
                )

                st.success(f"{len(registros)} ventas registradas correctamente.")

                st.rerun()

            except Exception as e:

                conn.rollback()
                st.error(e)

    # =================================
    # EDICIÓN / ELIMINACIÓN DE VENTAS
    # =================================

    st.divider()

    with st.expander("Editar o eliminar registros de ventas"):

        cantidad = st.selectbox(
            "Registros a mostrar",
            ["Últimos 20", "Últimos 100", "Todos"],
            key="ventas_registros_a_mostrar"
        )

        if cantidad == "Últimos 20":
            limit_sql = "LIMIT 20"
        elif cantidad == "Últimos 100":
            limit_sql = "LIMIT 100"
        else:
            limit_sql = ""

        query = f"""
            SELECT
                v.venta_id,
                f.nombre,
                v.fecha,
                v.tipo_registro,
                v.ventas_totales,
                COALESCE(v.venta_tarjeta, 0) AS venta_tarjeta,
                COALESCE(v.venta_efectivo, v.ventas_totales) AS venta_efectivo
            FROM ventas v
            JOIN farmacias f
                ON v.farmacia_id = f.farmacia_id
            ORDER BY v.created_at DESC
            {limit_sql};
        """

        cursor.execute(query)

        df_recent = pd.DataFrame(
            cursor.fetchall(),
            columns=[
                "venta_id",
                "farmacia",
                "fecha",
                "tipo_registro",
                "monto",
                "venta_tarjeta",
                "venta_efectivo"
            ]
        )

        st.dataframe(
            df_recent,
            use_container_width=True,
            hide_index=True
        )

        if not df_recent.empty:

            st.subheader("Editar registro de venta")

            opciones = {
                f"{row['farmacia']} | {row['fecha']} | ${row['monto']:,.2f}":
                row["venta_id"]
                for _, row in df_recent.iterrows()
            }

            seleccion = st.selectbox(
                "Selecciona el registro",
                options=list(opciones.keys()),
                key="ventas_seleccion_editar"
            )

            venta_id_seleccionada = opciones[seleccion]

            registro = df_recent[
                df_recent["venta_id"] == venta_id_seleccionada
            ].iloc[0]

            key_venta = f"venta_{venta_id_seleccionada}"

            farmacia_edit = st.selectbox(
                "Farmacia",
                farmacia_nombres,
                index=farmacia_nombres.index(registro["farmacia"]),
                key=f"ventas_edit_farmacia_{key_venta}"
            )

            fecha_edit = st.date_input(
                "Fecha",
                value=pd.to_datetime(registro["fecha"]).date(),
                key=f"ventas_edit_fecha_{key_venta}"
            )

            tipo_edit = st.selectbox(
                "Tipo de registro",
                ["diario"],
                index=0,
                key=f"ventas_edit_tipo_{key_venta}"
            )

            monto_edit = st.number_input(
                "Monto total",
                min_value=0.0,
                value=float(registro["monto"]),
                step=100.0,
                key=f"ventas_edit_monto_{key_venta}"
            )

            venta_tarjeta_edit = st.number_input(
                "Venta con tarjeta",
                min_value=0.0,
                value=float(registro["venta_tarjeta"]),
                step=100.0,
                key=f"ventas_edit_tarjeta_{key_venta}"
            )

            venta_efectivo_edit = monto_edit - venta_tarjeta_edit

            st.info(
                f"Efectivo estimado: ${venta_efectivo_edit:,.2f}"
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                if st.button(
                    "Guardar cambios",
                    use_container_width=True,
                    key=f"ventas_guardar_{key_venta}"
                ):

                    if monto_edit <= 0:
                        st.error("El monto debe ser mayor a 0.")
                        st.stop()

                    if venta_tarjeta_edit > monto_edit:
                        st.error("La venta con tarjeta no puede ser mayor a la venta total.")
                        st.stop()

                    try:

                        cursor.execute("""
                            UPDATE ventas
                            SET
                                farmacia_id = %s,
                                fecha = %s,
                                tipo_registro = %s,
                                ventas_totales = %s,
                                venta_tarjeta = %s,
                                venta_efectivo = %s
                            WHERE venta_id = %s;
                        """, (
                            farmacia_dict[farmacia_edit],
                            fecha_edit,
                            tipo_edit,
                            monto_edit,
                            venta_tarjeta_edit,
                            venta_efectivo_edit,
                            venta_id_seleccionada
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "MODIFICACION_VENTA",
                            f"Modificó venta ID {venta_id_seleccionada}"
                        )

                        st.success("Registro actualizado correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()
                        st.error(e)

            with col2:

                if st.button(
                    "Eliminar registro",
                    use_container_width=True,
                    key=f"ventas_eliminar_{key_venta}"
                ):

                    st.session_state["confirmar_eliminacion_venta"] = venta_id_seleccionada

            with col3:

                if st.button(
                    "Cancelar",
                    use_container_width=True,
                    key=f"ventas_cancelar_{key_venta}"
                ):

                    st.rerun()

            if (
                "confirmar_eliminacion_venta" in st.session_state
                and st.session_state["confirmar_eliminacion_venta"] == venta_id_seleccionada
            ):

                st.warning("Esta acción no se puede deshacer.")

                col_yes, col_no = st.columns(2)

                with col_yes:

                    if st.button(
                        "Sí, eliminar definitivamente",
                        key=f"ventas_confirmar_delete_{key_venta}"
                    ):

                        try:

                            cursor.execute("""
                                DELETE FROM ventas
                                WHERE venta_id = %s;
                            """, (
                                venta_id_seleccionada,
                            ))

                            conn.commit()

                            registrar_log(
                                st.session_state["usuario"],
                                "ELIMINACION_VENTA",
                                f"Eliminó venta ID {venta_id_seleccionada}"
                            )

                            del st.session_state["confirmar_eliminacion_venta"]

                            st.success("Registro eliminado correctamente.")

                            st.rerun()

                        except Exception as e:

                            conn.rollback()
                            st.error(e)

                with col_no:

                    if st.button(
                        "Cancelar eliminación",
                        key=f"ventas_cancelar_delete_{key_venta}"
                    ):

                        del st.session_state["confirmar_eliminacion_venta"]

                        st.rerun()


# ==================================================
# TAB 2 - REGISTRO DE GASTOS
# ==================================================

with tab2:

    st.subheader("Registro de gastos")

    categorias = [
        "Renta",
        "Sueldos",
        "Servicios",
        "Insumos",
        "Mercancia",
        "Transporte",
        "Otros"
    ]

    tipos_gasto = [
        "fijo",
        "variable"
    ]

    # =================================
    # REGISTRO DE GASTO
    # =================================

    st.subheader("Nuevo gasto")

    farmacia_nombre = st.selectbox(
        "Farmacia",
        farmacia_nombres,
        key="gastos_farmacia_nuevo"
    )

    farmacia_id = farmacia_dict[farmacia_nombre]

    categoria = st.selectbox(
        "Categoría",
        categorias,
        key="gastos_categoria_nuevo"
    )

    tipo_gasto = st.selectbox(
        "Tipo de gasto",
        tipos_gasto,
        key="gastos_tipo_nuevo"
    )

    fecha = st.date_input(
        "Fecha del gasto",
        value=date.today(),
        max_value=date.today(),
        key="gastos_fecha_nuevo"
    )

    monto = st.number_input(
        "Monto del gasto",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key="gastos_monto_nuevo"
    )

    descripcion = st.text_area(
        "Descripción del gasto",
        placeholder="Ej. Pago de renta de marzo, recibo CFE, compra de insumos, etc.",
        key="gastos_descripcion_nuevo"
    )

    folio = None

    if categoria == "Mercancia":

        folio = st.text_input(
            "Número de folio de la mercancía",
            placeholder="Ej. FOL-2025-001",
            key="gastos_folio_mercancia_nuevo"
        )

    if st.button(
        "Registrar gasto",
        key="btn_registrar_gasto"
    ):

        if monto <= 0:
            st.error("El monto debe ser mayor a 0.")
            st.stop()

        if categoria == "Mercancia" and not folio:
            st.error("Debes ingresar el número de folio para gastos de mercancía.")
            st.stop()

        if categoria == "Mercancia":

            if folio_mercancia_duplicado(cursor, farmacia_id, folio):
                st.error("Ya existe un gasto de mercancía con ese folio en esta farmacia.")
                st.stop()

        try:

            cursor.execute("""
                INSERT INTO gastos
                (
                    farmacia_id,
                    monto,
                    fecha,
                    tipo_gasto,
                    categoria,
                    descripcion,
                    folio
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
                );
            """, (
                farmacia_id,
                monto,
                fecha,
                tipo_gasto,
                categoria,
                descripcion,
                folio
            ))

            conn.commit()

            registrar_log(
                st.session_state["usuario"],
                "REGISTRO_GASTO",
                f"Registró gasto de ${monto:,.2f} ({categoria}) en {farmacia_nombre}"
            )

            st.success("Gasto registrado correctamente.")

            st.rerun()

        except Exception as e:

            conn.rollback()
            st.error(e)

    # =================================
    # EDICIÓN / ELIMINACIÓN DE GASTOS
    # =================================

    st.divider()

    with st.expander("Editar o eliminar registros de gastos"):

        cantidad = st.selectbox(
            "Registros a mostrar",
            ["Últimos 20", "Últimos 100", "Todos"],
            key="gastos_registros_a_mostrar"
        )

        if cantidad == "Últimos 20":
            limit_sql = "LIMIT 20"
        elif cantidad == "Últimos 100":
            limit_sql = "LIMIT 100"
        else:
            limit_sql = ""

        query = f"""
            SELECT 
                g.gasto_id,
                f.nombre AS farmacia,
                g.fecha,
                g.folio,
                g.categoria,
                g.tipo_gasto,
                g.descripcion,
                g.monto
            FROM gastos g
            JOIN farmacias f
                ON g.farmacia_id = f.farmacia_id
            ORDER BY g.created_at DESC
            {limit_sql};
        """

        cursor.execute(query)

        df_recent = pd.DataFrame(
            cursor.fetchall(),
            columns=[
                "gasto_id",
                "farmacia",
                "fecha",
                "folio",
                "categoria",
                "tipo_gasto",
                "descripcion",
                "monto"
            ]
        )

        st.dataframe(
            df_recent,
            use_container_width=True,
            hide_index=True
        )

        if not df_recent.empty:

            st.subheader("Editar gasto")

            opciones = {
                f"{row['farmacia']} | {row['fecha']} | {row['categoria']} | ${row['monto']:,.2f}":
                row["gasto_id"]
                for _, row in df_recent.iterrows()
            }

            seleccion = st.selectbox(
                "Selecciona el gasto",
                options=list(opciones.keys()),
                key="gastos_seleccion_editar"
            )

            gasto_id_seleccionado = opciones[seleccion]

            registro = df_recent[
                df_recent["gasto_id"] == gasto_id_seleccionado
            ].iloc[0]

            key_gasto = f"gasto_{gasto_id_seleccionado}"

            farmacia_edit = st.selectbox(
                "Farmacia",
                farmacia_nombres,
                index=farmacia_nombres.index(registro["farmacia"]),
                key=f"gastos_edit_farmacia_{key_gasto}"
            )

            fecha_edit = st.date_input(
                "Fecha",
                value=pd.to_datetime(registro["fecha"]).date(),
                key=f"gastos_edit_fecha_{key_gasto}"
            )

            categoria_edit = st.selectbox(
                "Categoría",
                categorias,
                index=categorias.index(registro["categoria"]),
                key=f"gastos_edit_categoria_{key_gasto}"
            )

            tipo_edit = st.selectbox(
                "Tipo de gasto",
                tipos_gasto,
                index=tipos_gasto.index(registro["tipo_gasto"]),
                key=f"gastos_edit_tipo_{key_gasto}"
            )

            folio_edit = st.text_input(
                "Folio",
                value="" if pd.isna(registro["folio"]) else str(registro["folio"]),
                key=f"gastos_edit_folio_{key_gasto}"
            )

            descripcion_edit = st.text_area(
                "Descripción",
                value="" if pd.isna(registro["descripcion"]) else str(registro["descripcion"]),
                key=f"gastos_edit_descripcion_{key_gasto}"
            )

            monto_edit = st.number_input(
                "Monto",
                min_value=0.0,
                value=float(registro["monto"]),
                step=100.0,
                key=f"gastos_edit_monto_{key_gasto}"
            )

            col1, col2, col3 = st.columns(3)

            with col1:

                if st.button(
                    "Guardar cambios",
                    use_container_width=True,
                    key=f"gastos_guardar_{key_gasto}"
                ):

                    if monto_edit <= 0:
                        st.error("El monto debe ser mayor a 0.")
                        st.stop()

                    if categoria_edit == "Mercancia" and folio_edit.strip() == "":
                        st.error("Debes ingresar folio para mercancía.")
                        st.stop()

                    try:

                        cursor.execute("""
                            UPDATE gastos
                            SET
                                farmacia_id = %s,
                                fecha = %s,
                                folio = %s,
                                categoria = %s,
                                tipo_gasto = %s,
                                descripcion = %s,
                                monto = %s
                            WHERE gasto_id = %s;
                        """, (
                            farmacia_dict[farmacia_edit],
                            fecha_edit,
                            folio_edit.strip(),
                            categoria_edit,
                            tipo_edit,
                            descripcion_edit.strip(),
                            monto_edit,
                            gasto_id_seleccionado
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "MODIFICACION_GASTO",
                            f"Modificó gasto ID {gasto_id_seleccionado}"
                        )

                        st.success("Gasto actualizado correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()
                        st.error(e)

            with col2:

                if st.button(
                    "Eliminar gasto",
                    use_container_width=True,
                    key=f"gastos_eliminar_{key_gasto}"
                ):

                    st.session_state["confirmar_eliminacion_gasto"] = gasto_id_seleccionado

            with col3:

                if st.button(
                    "Cancelar",
                    use_container_width=True,
                    key=f"gastos_cancelar_{key_gasto}"
                ):

                    st.rerun()

            if (
                "confirmar_eliminacion_gasto" in st.session_state
                and st.session_state["confirmar_eliminacion_gasto"] == gasto_id_seleccionado
            ):

                st.warning("Esta acción no se puede deshacer.")

                col_yes, col_no = st.columns(2)

                with col_yes:

                    if st.button(
                        "Sí, eliminar definitivamente",
                        key=f"gastos_confirmar_delete_{key_gasto}"
                    ):

                        try:

                            cursor.execute("""
                                DELETE FROM gastos
                                WHERE gasto_id = %s;
                            """, (
                                gasto_id_seleccionado,
                            ))

                            conn.commit()

                            registrar_log(
                                st.session_state["usuario"],
                                "ELIMINACION_GASTO",
                                f"Eliminó gasto ID {gasto_id_seleccionado}"
                            )

                            del st.session_state["confirmar_eliminacion_gasto"]

                            st.success("Gasto eliminado correctamente.")

                            st.rerun()

                        except Exception as e:

                            conn.rollback()
                            st.error(e)

                with col_no:

                    if st.button(
                        "Cancelar eliminación",
                        key=f"gastos_cancelar_delete_{key_gasto}"
                    ):

                        del st.session_state["confirmar_eliminacion_gasto"]

                        st.rerun()


# ===============================
# SIDEBAR INFO
# ===============================

st.sidebar.success(
    f"{st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button(
    "Cerrar sesión",
    key="btn_cerrar_sesion_registros"
):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")