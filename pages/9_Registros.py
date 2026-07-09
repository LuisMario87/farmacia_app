import streamlit as st

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

conn = get_connection()
cursor = conn.cursor()

st.title("Registros")

tab1, tab2 = st.tabs([
    "Registro de ventas",
    "Registro de gastos"
])

with tab1:
    st.subheader("Registro de ventas")

    # ---------------------------------
# FARMACIAS
# ---------------------------------
cursor.execute("SELECT farmacia_id, nombre FROM farmacias ORDER BY nombre;")
farmacias = cursor.fetchall()
farmacia_dict = {f[1]: f[0] for f in farmacias}
farmacia_reverse = {f[0]: f[1] for f in farmacias}
farmacia_nombres = list(farmacia_dict.keys())

# =================================
# MODO DE REGISTRO
# =================================
modo = st.radio(
    "Modo de registro",
    [
        "Registro Individual",
        "Registro Rápido (Todas las farmacias)",
        "Registro Personalizado"
    ]
)

# =================================
# DATOS COMUNES
# =================================
tipo_registro = st.selectbox(
    "Tipo de registro",
    ["diario"]
)

fecha = st.date_input(
    "Fecha de la venta",
    value=date.today(),
    max_value=date.today()
)
def venta_duplicada(cursor, farmacia_id, fecha):
    cursor.execute("""
        SELECT 1
        FROM ventas
        WHERE farmacia_id = %s
        AND fecha = %s
        LIMIT 1
    """, (farmacia_id, fecha))
    return cursor.fetchone() is not None

st.divider()

# =================================
# REGISTRO INDIVIDUAL
# =================================
if modo == "Registro Individual":

    st.subheader("🏥 Registro Individual")

    farmacia_nombre = st.selectbox("Farmacia", farmacia_nombres)
    farmacia_id = farmacia_dict[farmacia_nombre]

    monto = st.number_input(
        "Monto de venta",
        min_value=0.0,
        step=500.0,
        format="%.2f"
    )

    venta_tarjeta = st.number_input(
    "💳 Venta con tarjeta",
    min_value=0.0,
    step=100.0,
    format="%.2f"
    )

    venta_efectivo = monto - venta_tarjeta

    st.info(
        f"💵 Efectivo estimado: ${venta_efectivo:,.2f}"
    )

    if st.button("💾 Registrar venta"):
        if monto <= 0:
            st.error("❌ El monto debe ser mayor a 0")
            st.stop()
        
        if venta_duplicada(cursor, farmacia_id, fecha):
            st.error("❌ Ya existe una venta registrada para esta farmacia en esa fecha")
            st.stop()

        if venta_tarjeta > monto:
            st.error(
                "La venta con tarjeta no puede ser mayor a la venta total"
            )
            st.stop()
        try:
            cursor.execute("""
                INSERT INTO ventas (
                farmacia_id,
                ventas_totales,
                venta_tarjeta,
                venta_efectivo,
                tipo_registro,
                fecha
                )
                VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
                )
                """, (farmacia_id, monto, tipo_registro, fecha)
            )

            conn.commit()
            st.success("✅ Venta registrada correctamente")
        
            registrar_log(
                st.session_state["usuario"],
                "REGISTRO_VENTA",
                f"Registró una venta de ${monto:,.2f} en {farmacia_nombre} ({fecha})"
            )
    
        except Exception as e:
            conn.rollback()
            st.error(e)

# =================================
# REGISTRO RÁPIDO (TODAS)
# =================================
if modo == "Registro Rápido (Todas las farmacias)":

    st.subheader("⚡ Registro Rápido")

    registros = []

    for nombre, fid in farmacia_dict.items():
        monto = st.number_input(
            nombre,
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"rapido_{fid}"
        )
        tarjeta = st.number_input(
        f"{nombre} - Tarjeta",
        min_value=0.0,
        step=100.0,
        format="%.2f",
        key=f"tarjeta_{fid}"
        )
        efectivo = monto - tarjeta

        if tarjeta > monto:
            st.error(
                f"{nombre}: tarjeta mayor que venta"
            )
            st.stop()

        if monto > 0:
            if venta_duplicada(cursor, fid, fecha):
                st.warning(f"⚠️ {nombre} ya tiene venta registrada ese día, se omitió")
            else:
                registros.append((fid, monto, tipo_registro, fecha))


    if st.button("💾 Registrar ventas"):
        if not registros:
            st.warning("⚠️ No hay montos válidos")
            st.stop()

        try:
            cursor.executemany("""
                INSERT INTO ventas (farmacia_id, ventas_totales, tipo_registro, fecha)
                VALUES (%s, %s, %s, %s)
            """, registros)

            conn.commit()
            st.success(f"✅ {len(registros)} ventas registradas")

            registrar_log(
                st.session_state["usuario"],
                "REGISTRO_VENTA",
                f"Registró {len(registros)} ventas personalizadas ({fecha})"
            )


            
        except Exception as e:
            conn.rollback()
            st.error(e)

# =================================
# REGISTRO PERSONALIZADO
# =================================
if modo == "Registro Personalizado":

    st.subheader("🎯 Registro Personalizado")

    seleccionadas = st.multiselect(
        "Selecciona farmacias",
        farmacia_nombres
    )

    registros = []

    for nombre in seleccionadas:
        fid = farmacia_dict[nombre]
        monto = st.number_input(
            nombre,
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"custom_{fid}"
        )

        if monto > 0:
            if venta_duplicada(cursor, fid, fecha):
                st.warning(f"⚠️ {nombre} ya tiene venta registrada ese día, se omitió")
            else:
                registros.append((fid, monto, tipo_registro, fecha))


    if st.button("💾 Registrar ventas seleccionadas"):
        if not registros:
            st.warning("⚠️ No hay montos válidos")
            st.stop()

        try:
            cursor.executemany("""
                INSERT INTO ventas (farmacia_id, ventas_totales, tipo_registro, fecha)
                VALUES (%s, %s, %s, %s)
            """, registros)

            conn.commit()
            st.success(f"✅ {len(registros)} ventas registradas")

            registrar_log(
                st.session_state["usuario"],
                "REGISTRO_VENTA",
                f"Registró {len(registros)} ventas (registro rápido) ({fecha})"
            )



        except Exception as e:
            conn.rollback()
            st.error(e)


# =================================
# EDICIÓN / ELIMINACIÓN
# =================================
st.divider()

with st.expander("⚠️ ¿Cometiste un error? Editar o eliminar registros"):

    cantidad = st.selectbox(
        "📄 Registros a mostrar",
        ["Últimos 20", "Últimos 100", "Todos"]
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
            v.ventas_totales
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
            "monto"
        ]
    )

    # -------------------------
    # TABLA SOLO LECTURA
    # -------------------------
    st.dataframe(
        df_recent,
        use_container_width=True,
        hide_index=True
    )

    if not df_recent.empty:

        st.subheader("✏️ Editar registro")

        opciones = {
            f"{row['farmacia']} | {row['fecha']} | ${row['monto']:,.2f}":
            row["venta_id"]
            for _, row in df_recent.iterrows()
        }

        seleccion = st.selectbox(
            "Selecciona el registro",
            options=list(opciones.keys())
        )

        venta_id_seleccionada = opciones[seleccion]

        registro = df_recent[
            df_recent["venta_id"] == venta_id_seleccionada
        ].iloc[0]

        farmacia_edit = st.selectbox(
            "Farmacia",
            farmacia_nombres,
            index=farmacia_nombres.index(
                registro["farmacia"]
            )
        )

        fecha_edit = st.date_input(
            "Fecha",
            value=pd.to_datetime(
                registro["fecha"]
            ).date()
        )

        tipo_edit = st.selectbox(
            "Tipo de registro",
            ["diario"],
            index=0,
            key="edit_tipo_registro"
        )

        monto_edit = st.number_input(
            "Monto",
            min_value=0.0,
            value=float(registro["monto"]),
            step=100.0
        )

        col1, col2, col3 = st.columns(3)

        # -------------------------
        # GUARDAR
        # -------------------------
        with col1:
            if st.button(
                "💾 Guardar cambios",
                use_container_width=True
            ):
                try:

                    cursor.execute("""
                        UPDATE ventas
                        SET
                            farmacia_id = %s,
                            fecha = %s,
                            tipo_registro = %s,
                            ventas_totales = %s
                        WHERE venta_id = %s
                    """, (
                        farmacia_dict[farmacia_edit],
                        fecha_edit,
                        tipo_edit,
                        monto_edit,
                        venta_id_seleccionada
                    ))

                    conn.commit()

                    registrar_log(
                        st.session_state["usuario"],
                        "MODIFICACION_VENTA",
                        f"Modificó venta ID {venta_id_seleccionada}"
                    )

                    st.success(
                        "✅ Registro actualizado correctamente"
                    )

                    st.rerun()

                except Exception as e:
                    conn.rollback()
                    st.error(e)

        # -------------------------
        # ELIMINAR
        # -------------------------
        with col2:
            if st.button(
                "🗑 Eliminar registro",
                use_container_width=True
            ):
                st.session_state[
                    "confirmar_eliminacion"
                ] = venta_id_seleccionada

        # -------------------------
        # CANCELAR
        # -------------------------
        with col3:
            if st.button(
                "❌ Cancelar",
                use_container_width=True
            ):
                st.rerun()

        # -------------------------
        # CONFIRMACIÓN ELIMINAR
        # -------------------------
        if (
            "confirmar_eliminacion"
            in st.session_state
            and
            st.session_state["confirmar_eliminacion"]
            == venta_id_seleccionada
        ):

            st.warning(
                "⚠️ Esta acción no se puede deshacer"
            )

            col_yes, col_no = st.columns(2)

            with col_yes:
                if st.button(
                    "✅ Sí, eliminar definitivamente"
                ):
                    try:

                        cursor.execute("""
                            DELETE FROM ventas
                            WHERE venta_id = %s
                        """, (
                            venta_id_seleccionada,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "ELIMINACION_VENTA",
                            f"Eliminó venta ID {venta_id_seleccionada}"
                        )

                        del st.session_state[
                            "confirmar_eliminacion"
                        ]

                        st.success(
                            "🗑 Registro eliminado correctamente"
                        )

                        st.rerun()

                    except Exception as e:
                        conn.rollback()
                        st.error(e)

            with col_no:
                if st.button("Cancelar eliminación"):

                    del st.session_state[
                        "confirmar_eliminacion"
                    ]

                    st.rerun()


with tab2:
    st.subheader("Registro de gastos")

    # Aquí vas a pegar TODO el contenido de tu archivo:
    # 4_Registro_Gastos.py
    # pero sin repetir imports, sin repetir seguridad y sin repetir set_page_config.


# ===============================
# SIDEBAR INFO
# ===============================
st.sidebar.success(
    f"{st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")