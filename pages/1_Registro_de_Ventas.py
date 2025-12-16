import streamlit as st
from datetime import date
import psycopg2
from utils.conexionASupabase import get_connection

st.set_page_config(page_title="Registro de Ventas", layout="wide")
st.title("📝 Registro de Ventas por Farmacia")

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

# =================================
# SELECCIÓN DE MODO
# =================================
modo = st.radio(
    "Modo de registro",
    ["Registro Individual", "Registro Rápido (Todas las farmacias)"]
)

# =================================
# DATOS COMUNES
# =================================
tipo_registro = st.selectbox(
    "Tipo de registro",
    ["diario", "semanal", "mensual"]
)

fecha = st.date_input(
    "Fecha de la venta",
    value=date.today(),
    max_value=date.today()
)

anio = fecha.year
mes = fecha.month
dia = fecha.day
semana = (dia - 1) // 7 + 1  # Semana 1–4

st.divider()

# =================================
# 1️⃣ REGISTRO INDIVIDUAL
# =================================
if modo == "Registro Individual":

    st.subheader("🏥 Registro Individual")

    farmacia_nombre = st.selectbox("Selecciona la farmacia", farmacia_dict.keys())
    farmacia_id = farmacia_dict[farmacia_nombre]

    monto = st.number_input(
        "Monto de la venta ($)",
        min_value=0.0,
        step=500.0,
        format="%.2f"
    )

    if st.button("💾 Registrar Venta Individual"):
        if monto <= 0:
            st.error("❌ El monto debe ser mayor a 0.")
            st.stop()

        try:
            cursor.execute("""
                INSERT INTO ventas (farmacia_id, ventas_totales, tipo_registro, semana, mes, anio)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                farmacia_id,
                monto,
                tipo_registro,
                semana if tipo_registro != "mensual" else None,
                mes,
                anio
            ))

            conn.commit()
            st.success(f"✅ Venta registrada para {farmacia_nombre}")

        except Exception as e:
            st.error(f"Error: {e}")

# =================================
# 2️⃣ REGISTRO RÁPIDO (TODAS)
# =================================
if modo == "Registro Rápido (Todas las farmacias)":

    st.subheader("⚡ Registro Rápido para Todas las Farmacias")
    st.caption("Ingresa los montos y guarda todo en un solo clic")

    ventas_rapidas = {}

    for nombre, fid in farmacia_dict.items():
        ventas_rapidas[fid] = st.number_input(
            f"{nombre}",
            min_value=0.0,
            step=500.0,
            format="%.2f",
            key=f"rapido_{fid}"
        )

    if st.button("💾 Registrar Ventas Masivas"):
        registros = []

        for fid, monto in ventas_rapidas.items():
            if monto > 0:
                registros.append((
                    fid,
                    monto,
                    tipo_registro,
                    semana if tipo_registro != "mensual" else None,
                    mes,
                    anio
                ))

        if not registros:
            st.warning("⚠️ No se ingresaron montos válidos.")
            st.stop()

        try:
            cursor.executemany("""
                INSERT INTO ventas (farmacia_id, ventas_totales, tipo_registro, semana, mes, anio)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, registros)

            conn.commit()
            st.success(f"✅ Se registraron {len(registros)} ventas correctamente")

        except Exception as e:
            st.error(f"Error al registrar ventas: {e}")

# ---------------------------------
# CIERRE
# ---------------------------------
cursor.close()
conn.close()
