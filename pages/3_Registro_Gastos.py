import streamlit as st
import pandas as pd
from datetime import date
from utils.conexionASupabase import get_connection

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
# CATEGORÍAS Y TIPOS DE GASTO
# ---------------------------------
categorias = [
    "Renta", "Sueldos", "Servicios",
    "Insumos", "Transporte", "Otros"
]

tipos_gasto = ["fijo", "variable"]

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

if st.button("💾 Registrar gasto"):
    if monto <= 0:
        st.error("❌ El monto debe ser mayor a 0")
        st.stop()

    try:
        cursor.execute("""
            INSERT INTO gastos (farmacia_id, monto, fecha, tipo_gasto, categoria)
            VALUES (%s, %s, %s, %s, %s)
        """, (farmacia_id, monto, fecha, tipo_gasto, categoria))

        conn.commit()
        st.success("✅ Gasto registrado correctamente")

    except Exception as e:
        conn.rollback()
        st.error(e)

# =================================
# EDICIÓN / ELIMINACIÓN
# =================================
st.divider()

with st.expander("⚠️ Editar o eliminar gastos registrados"):

    cantidad = st.selectbox(
        "📄 Registros a mostrar",
        ["Últimos 20", "Últimos 100", "Todos"]
    )

    limit_sql = (
        "LIMIT 20" if cantidad == "Últimos 20"
        else "LIMIT 100" if cantidad == "Últimos 100"
        else ""
    )

    query = f"""
        SELECT 
            g.gasto_id,
            f.nombre AS farmacia,
            g.fecha,
            g.categoria,
            g.tipo_gasto,
            g.monto
        FROM gastos g
        JOIN farmacias f ON g.farmacia_id = f.farmacia_id
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
            "categoria",
            "tipo_gasto",
            "monto"
        ]
    )

    edited = st.data_editor(
        df_recent,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "farmacia": st.column_config.SelectboxColumn(
                "Farmacia",
                options=farmacia_nombres
            ),
            "categoria": st.column_config.SelectboxColumn(
                "Categoría",
                options=categorias
            ),
            "tipo_gasto": st.column_config.SelectboxColumn(
                "Tipo de gasto",
                options=tipos_gasto
            )
        }
    )

    if st.button("💾 Guardar cambios"):
        try:
            for _, r in edited.iterrows():
                cursor.execute("""
                    UPDATE gastos
                    SET
                        farmacia_id = %s,
                        fecha = %s,
                        categoria = %s,
                        tipo_gasto = %s,
                        monto = %s
                    WHERE gasto_id = %s
                """, (
                    farmacia_dict[r["farmacia"]],
                    r["fecha"],
                    r["categoria"],
                    r["tipo_gasto"],
                    r["monto"],
                    r["gasto_id"]
                ))

            conn.commit()
            st.success("✅ Cambios guardados correctamente")

        except Exception as e:
            conn.rollback()
            st.error(e)

    st.subheader("🗑 Eliminar gasto")

    borrar_id = st.selectbox(
        "Selecciona el gasto a eliminar",
        df_recent["gasto_id"]
    )

    if st.button("❌ Eliminar gasto"):
        try:
            cursor.execute(
                "DELETE FROM gastos WHERE gasto_id = %s",
                (borrar_id,)
            )
            conn.commit()
            st.success("🗑 Gasto eliminado correctamente")

        except Exception as e:
            conn.rollback()
            st.error(e)

# ---------------------------------
# SIDEBAR
# ---------------------------------
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("login.py")

# ---------------------------------
# CIERRE
# ---------------------------------
cursor.close()
conn.close()
