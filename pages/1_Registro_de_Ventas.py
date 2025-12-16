import streamlit as st
import pandas as pd
from utils.conexionASupabase import get_connection

st.title("📝 Registro de Ventas")

conn = get_connection()
cursor = conn.cursor()

# Obtener farmacias
cursor.execute("SELECT farmacia_id, nombre FROM farmacias ORDER BY farmacia_id;")
farmacias = cursor.fetchall()
df_farmacias = pd.DataFrame(farmacias, columns=["id", "nombre"])

st.subheader("Registrar nueva venta")

with st.form("registro_ventas"):
    farmacia = st.selectbox("Farmacia", df_farmacias["nombre"])

    tipo_registro = st.selectbox(
        "Tipo de registro",
        ["diario", "semanal", "mensual"]
    )

    dia = None
    semana = None

    if tipo_registro == "diario":
        dia = st.selectbox("Día del mes", list(range(1, 32)))

    elif tipo_registro == "semanal":
        semana = st.selectbox("Semana del mes", [1, 2, 3, 4])

    mes = st.selectbox("Mes", list(range(1, 13)))
    anio = st.number_input("Año", min_value=2025, max_value=2035, value=2025)

    monto = st.number_input(
        "Monto total vendido",
        min_value=0.0,
        step=100.0
    )

    guardar = st.form_submit_button("Guardar venta")

if guardar:
    farmacia_id = int(df_farmacias[df_farmacias["nombre"] == farmacia]["id"].iloc[0])

    cursor.execute("""
        INSERT INTO ventas (
            farmacia_id, ventas_totales, tipo_registro,
            dia, semana, mes, anio
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        farmacia_id, monto, tipo_registro,
        dia, semana, mes, anio
    ))

    conn.commit()
    st.success("✅ Venta registrada correctamente")

conn.close()
