import streamlit as st
import pandas as pd
from datetime import date
from utils.conexionASupabase import get_connection

st.set_page_config(page_title="Registro de Ventas", layout="wide")
st.title("📝 Registro de Ventas por Farmacia")

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
    ["diario", "semanal", "mensual"]
)

fecha = st.date_input(
    "Fecha de la venta",
    value=date.today(),
    max_value=date.today()
)

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

    if st.button("💾 Registrar venta"):
        if monto <= 0:
            st.error("❌ El monto debe ser mayor a 0")
            st.stop()

        try:
            cursor.execute("""
                INSERT INTO ventas (farmacia_id, ventas_totales, tipo_registro, fecha)
                VALUES (%s, %s, %s, %s)
            """, (farmacia_id, monto, tipo_registro, fecha))

            conn.commit()
            st.success("✅ Venta registrada correctamente")

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

        if monto > 0:
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
        SELECT v.venta_id, f.nombre, v.fecha, v.tipo_registro, v.ventas_totales
        FROM ventas v
        JOIN farmacias f ON v.farmacia_id = f.farmacia_id
        ORDER BY v.created_at DESC
        {limit_sql};
    """

    cursor.execute(query)

    df_recent = pd.DataFrame(
        cursor.fetchall(),
        columns=["venta_id", "farmacia", "fecha", "tipo_registro", "monto"]
    )

    # Column config para desplegables
    edited = st.data_editor(
        df_recent,
        use_container_width=True,
        num_rows="fixed",
        column_config={
            "farmacia": st.column_config.SelectboxColumn(
                "Farmacia",
                options=farmacia_nombres
            ),
            "tipo_registro": st.column_config.SelectboxColumn(
                "Tipo de registro",
                options=["diario", "semanal", "mensual"]
            )
        }
    )

    if st.button("💾 Guardar cambios"):
        try:
            for _, r in edited.iterrows():
                cursor.execute("""
                    UPDATE ventas
                    SET 
                        farmacia_id = %s,
                        fecha = %s,
                        tipo_registro = %s,
                        ventas_totales = %s
                    WHERE venta_id = %s
                """, (
                    farmacia_dict[r["farmacia"]],
                    r["fecha"],
                    r["tipo_registro"],
                    r["monto"],
                    r["venta_id"]
                ))

            conn.commit()
            st.success("✅ Cambios guardados correctamente")

        except Exception as e:
            conn.rollback()
            st.error(e)

    st.subheader("🗑 Eliminar registro")

    borrar_id = st.selectbox(
        "Selecciona el ID a eliminar",
        df_recent["venta_id"]
    )

    if st.button("❌ Eliminar"):
        try:
            cursor.execute(
                "DELETE FROM ventas WHERE venta_id = %s",
                (borrar_id,)
            )
            conn.commit()
            st.success("🗑 Registro eliminado correctamente")

        except Exception as e:
            conn.rollback()
            st.error(e)


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






