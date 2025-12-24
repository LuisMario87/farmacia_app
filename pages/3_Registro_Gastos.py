import streamlit as st
from datetime import date
import psycopg2
from utils.conexionASupabase import get_connection

st.set_page_config(page_title="Registro de Gastos", layout="wide")
st.title("💸 Registro de Gastos por Farmacia")

# ---------------------------------
# BLOQUEO POR SESIÓN
# ---------------------------------
if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

# ---------------------------------
# CONEXIÓN
# ---------------------------------
conn = get_connection()
cursor = conn.cursor()

# ---------------------------------
# OBTENER FARMACIAS
# ---------------------------------
cursor.execute("SELECT farmacia_id, nombre FROM farmacias ORDER BY nombre;")
farmacias = cursor.fetchall()
farmacia_dict = {f[1]: f[0] for f in farmacias}

# ---------------------------------
# FORMULARIO
# ---------------------------------
st.subheader("📝 Nuevo Gasto")

col1, col2, col3 = st.columns(3)

with col1:
    farmacia_nombre = st.selectbox("Farmacia", farmacia_dict.keys())
    farmacia_id = farmacia_dict[farmacia_nombre]

with col2:
    fecha = st.date_input(
        "Fecha del gasto",
        value=date.today(),
        max_value=date.today()
    )

with col3:
    tipo_gasto = st.selectbox(
        "Tipo de gasto",
        ["fijo", "variable"]
    )

categoria = st.selectbox(
    "Categoría del gasto",
    [
        "Renta",
        "Servicios (Luz, Agua, Internet)",
        "Sueldos",
        "Insumos",
        "Mantenimiento",
        "Transporte",
        "Impuestos",
        "Otro"
    ]
)

descripcion = st.text_area(
    "Descripción (opcional)",
    placeholder="Ej. Pago de renta correspondiente a marzo"
)

monto = st.number_input(
    "Monto del gasto ($)",
    min_value=0.0,
    step=100.0,
    format="%.2f"
)

# ---------------------------------
# GUARDAR
# ---------------------------------
if st.button("💾 Registrar Gasto"):
    if monto <= 0:
        st.error("❌ El monto debe ser mayor a 0")
        st.stop()

    try:
        cursor.execute("""
            INSERT INTO gastos (
                farmacia_id,
                fecha,
                categoria,
                descripcion,
                monto,
                tipo_gasto
            )
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            farmacia_id,
            fecha,
            categoria,
            descripcion,
            monto,
            tipo_gasto
        ))

        conn.commit()
        st.success("✅ Gasto registrado correctamente")

    except Exception as e:
        st.error(f"Error al registrar gasto: {e}")

# ---------------------------------
# CIERRE
# ---------------------------------
cursor.close()
conn.close()
