import streamlit as st
import pandas as pd
from datetime import date
from utils.conexionASupabase import get_connection
from utils.logger import registrar_log

st.set_page_config(page_title="Registro de Gastos", layout="wide")
st.title("💸 Registro de Gastos por Farmacia")

# ---------------------------------
# CONEXIÓN
# ---------------------------------
conn = get_connection()
cursor = conn.cursor()

# Bloquear acceso si no hay sesión
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

# ---------------------------------
# FARMACIAS
# ---------------------------------
cursor.execute("SELECT farmacia_id, nombre FROM farmacias ORDER BY nombre;")
farmacias = cursor.fetchall()
farmacia_dict = {f[1]: f[0] for f in farmacias}
farmacia_nombres = list(farmacia_dict.keys())

# ---------------------------------
# CATEGORÍAS Y TIPOS DE GASTO ETC
# ---------------------------------
categorias = [
    "Renta", "Sueldos", "Servicios",
    "Insumos","Mercancia","Transporte", "Otros"
]

tipos_gasto = ["fijo", "variable"]

def folio_mercancia_duplicado(cursor, farmacia_id, folio):
    cursor.execute("""
        SELECT 1
        FROM gastos
        WHERE farmacia_id = %s
        AND categoria = 'Mercancia'
        AND folio = %s
        LIMIT 1
    """, (farmacia_id, folio))
    return cursor.fetchone() is not None


# =================================
# REGISTRO DE GASTO
# =================================
st.subheader("📝 Nuevo gasto")

farmacia_nombre = st.selectbox("Farmacia", farmacia_nombres)
farmacia_id = farmacia_dict[farmacia_nombre]

categoria = st.selectbox("Categoría", categorias)
tipo_gasto = st.selectbox("Tipo de gasto", tipos_gasto)

fecha = st.date_input(
    "Fecha del gasto",
    value=date.today(),
    max_value=date.today()
)

monto = st.number_input(
    "Monto del gasto",
    min_value=0.0,
    step=100.0,
    format="%.2f"
)

descripcion = st.text_area(
    "Descripción del gasto",
    placeholder="Ej. Pago de renta de marzo, recibo CFE, compra de insumos, etc."
)

folio = None

if categoria == "Mercancia":
    folio = st.text_input(
        "🧾 Número de folio de la mercancía",
        placeholder="Ej. FOL-2025-001"
    )


if st.button("💾 Registrar gasto"):
    if monto <= 0:
        st.error("❌ El monto debe ser mayor a 0")
        st.stop()
    
    if categoria == "Mercancia" and not folio:
        st.error("❌ Debes ingresar el número de folio para gastos de mercancía")
        st.stop()
    
    if categoria == "Mercancia":
        if folio_mercancia_duplicado(cursor, farmacia_id, folio):
            st.error("❌ Ya existe un gasto de mercancía con ese folio en esta farmacia")
            st.stop()


    try:
        cursor.execute("""
            INSERT INTO gastos (
                farmacia_id, monto, fecha, tipo_gasto, categoria, descripcion, folio
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
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
        st.success("✅ Gasto registrado correctamente")

        registrar_log(
            st.session_state["usuario"],
            "REGISTRO_GASTO",
            f"Registró gasto de ${monto:,.2f} ({categoria}) en {farmacia_nombre}"
        )


    except Exception as e:
        conn.rollback()
        st.error(e)

# =================================
# EDICIÓN / ELIMINACIÓN
# =================================
    # -------------------------
    # TABLA SOLO LECTURA
    # -------------------------
    st.dataframe(
        df_recent,
        use_container_width=True,
        hide_index=True
    )

    if not df_recent.empty:

        st.subheader("✏️ Editar gasto")

        opciones = {
            f"{row['farmacia']} | {row['fecha']} | {row['categoria']} | ${row['monto']:,.2f}":
            row["gasto_id"]
            for _, row in df_recent.iterrows()
        }

        seleccion = st.selectbox(
            "Selecciona el gasto",
            options=list(opciones.keys()),
            key="seleccion_gasto"
        )

        gasto_id_seleccionado = opciones[seleccion]

        registro = df_recent[
            df_recent["gasto_id"] == gasto_id_seleccionado
        ].iloc[0]

        farmacia_edit = st.selectbox(
            "Farmacia",
            farmacia_nombres,
            index=farmacia_nombres.index(
                registro["farmacia"]
            ),
            key=f"edit_farmacia_{gasto_id_seleccionado}"
        )

        fecha_edit = st.date_input(
            "Fecha",
            value=pd.to_datetime(
                registro["fecha"]
            ).date(),
            key=f"edit_fecha_{gasto_id_seleccionado}"
        )

        categoria_edit = st.selectbox(
            "Categoría",
            categorias,
            index=categorias.index(
                registro["categoria"]
            ),
            key=f"edit_categoria_{gasto_id_seleccionado}"
        )

        tipo_edit = st.selectbox(
            "Tipo de gasto",
            tipos_gasto,
            index=tipos_gasto.index(
                registro["tipo_gasto"]
            ),
            key=f"edit_tipo_{gasto_id_seleccionado}"
        )

        folio_edit = st.text_input(
            "Folio",
            value="" if pd.isna(registro["folio"]) else str(registro["folio"]),
            key=f"edit_folio_{gasto_id_seleccionado}"
        )

        descripcion_edit = st.text_area(
            "Descripción",
            value="" if pd.isna(registro["descripcion"]) else str(registro["descripcion"]),
            key=f"edit_descripcion_{gasto_id_seleccionado}"
        )

        monto_edit = st.number_input(
            "Monto",
            min_value=0.0,
            value=float(registro["monto"]),
            step=100.0,
            key=f"edit_monto_{gasto_id_seleccionado}"
        )

        col1, col2, col3 = st.columns(3)

        # -------------------------
        # GUARDAR
        # -------------------------
        with col1:

            if st.button(
                "💾 Guardar cambios",
                use_container_width=True,
                key=f"guardar_{gasto_id_seleccionado}"
            ):

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
                        WHERE gasto_id = %s
                    """, (
                        farmacia_dict[farmacia_edit],
                        fecha_edit,
                        folio_edit,
                        categoria_edit,
                        tipo_edit,
                        descripcion_edit,
                        monto_edit,
                        gasto_id_seleccionado
                    ))

                    conn.commit()

                    registrar_log(
                        st.session_state["usuario"],
                        "MODIFICACION_GASTO",
                        f"Modificó gasto ID {gasto_id_seleccionado}"
                    )

                    st.success(
                        "✅ Gasto actualizado correctamente"
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
                "🗑 Eliminar gasto",
                use_container_width=True,
                key=f"eliminar_{gasto_id_seleccionado}"
            ):

                st.session_state[
                    "confirmar_eliminacion_gasto"
                ] = gasto_id_seleccionado

        # -------------------------
        # CANCELAR
        # -------------------------
        with col3:

            if st.button(
                "❌ Cancelar",
                use_container_width=True,
                key=f"cancelar_{gasto_id_seleccionado}"
            ):

                st.rerun()

        # -------------------------
        # CONFIRMAR ELIMINACIÓN
        # -------------------------
        if (
            "confirmar_eliminacion_gasto"
            in st.session_state
            and
            st.session_state[
                "confirmar_eliminacion_gasto"
            ] == gasto_id_seleccionado
        ):

            st.warning(
                "⚠️ Esta acción no se puede deshacer"
            )

            col_yes, col_no = st.columns(2)

            with col_yes:

                if st.button(
                    "✅ Sí, eliminar definitivamente",
                    key=f"confirmar_{gasto_id_seleccionado}"
                ):

                    try:

                        cursor.execute("""
                            DELETE FROM gastos
                            WHERE gasto_id = %s
                        """, (
                            gasto_id_seleccionado,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "ELIMINACION_GASTO",
                            f"Eliminó gasto ID {gasto_id_seleccionado}"
                        )

                        del st.session_state[
                            "confirmar_eliminacion_gasto"
                        ]

                        st.success(
                            "🗑 Gasto eliminado correctamente"
                        )

                        st.rerun()

                    except Exception as e:
                        conn.rollback()
                        st.error(e)

            with col_no:

                if st.button(
                    "Cancelar eliminación",
                    key=f"cancelar_delete_{gasto_id_seleccionado}"
                ):

                    del st.session_state[
                        "confirmar_eliminacion_gasto"
                    ]

                    st.rerun()
# ---------------------------------
# SIDEBAR
# ---------------------------------
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")

# ---------------------------------
# CIERRE
# ---------------------------------
cursor.close()
conn.close()
