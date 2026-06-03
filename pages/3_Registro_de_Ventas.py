import streamlit as st
import pandas as pd
from datetime import date
from utils.conexionASupabase import get_connection
from utils.logger import registrar_log

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

    if st.button("💾 Registrar venta"):
        if monto <= 0:
            st.error("❌ El monto debe ser mayor a 0")
            st.stop()
        
        if venta_duplicada(cursor, farmacia_id, fecha):
            st.error("❌ Ya existe una venta registrada para esta farmacia en esa fecha")
            st.stop()


        try:
            cursor.execute("""
                INSERT INTO ventas (farmacia_id, ventas_totales, tipo_registro, fecha)
                VALUES (%s, %s, %s, %s)
            """, (farmacia_id, monto, tipo_registro, fecha))

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
# EDICIÓN / ELIMINACIÓN (SUSTITUIR)
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
        SELECT v.venta_id, v.farmacia_id, f.nombre, v.fecha, v.tipo_registro, v.ventas_totales
        FROM ventas v
        JOIN farmacias f ON v.farmacia_id = f.farmacia_id
        ORDER BY v.created_at DESC
        {limit_sql};
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    if not rows:
        st.info("No hay registros para mostrar.")
    else:
        df_recent = pd.DataFrame(rows, columns=["venta_id", "farmacia_id", "farmacia", "fecha", "tipo_registro", "monto"])

        st.markdown("### Registros recientes")
        st.dataframe(df_recent[["venta_id", "farmacia", "fecha", "tipo_registro", "monto"]], use_container_width=True)

        # Seleccionar venta por ID
        venta_ids = df_recent["venta_id"].tolist()
        selected_id = st.selectbox("Selecciona la venta a editar/eliminar (ID)", venta_ids)

        # Cargar datos de la venta seleccionada
        selected_row = df_recent[df_recent["venta_id"] == selected_id].iloc[0]

        st.subheader("Editar venta")
        farmacia_actual = farmacia_reverse[selected_row["farmacia_id"]]
        farmacia_nuevo = st.selectbox("Farmacia", farmacia_nombres, index=farmacia_nombres.index(farmacia_actual))
        fecha_nueva = st.date_input("Fecha", value=pd.to_datetime(selected_row["fecha"]).date())
        tipo_nuevo = st.selectbox("Tipo de registro", ["diario", "semanal", "mensual"], index=["diario", "semanal", "mensual"].index(selected_row["tipo_registro"]))
        monto_nuevo = st.number_input("Monto", min_value=0.0, step=500.0, format="%.2f", value=float(selected_row["monto"]))

        def venta_duplicada_update(cursor, farmacia_id, fecha, venta_id):
            cursor.execute("""
                SELECT 1 FROM ventas
                WHERE farmacia_id = %s AND fecha = %s AND venta_id <> %s
                LIMIT 1
            """, (farmacia_id, fecha, venta_id))
            return cursor.fetchone() is not None

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 Guardar cambios"):
                if monto_nuevo <= 0:
                    st.error("❌ El monto debe ser mayor a 0")
                else:
                    fid_nuevo = farmacia_dict[farmacia_nuevo]
                    if venta_duplicada_update(cursor, fid_nuevo, fecha_nueva, selected_id):
                        st.error("❌ Ya existe una venta para esa farmacia y fecha (otro registro).")
                    else:
                        try:
                            cursor.execute("""
                                UPDATE ventas
                                SET farmacia_id = %s, fecha = %s, tipo_registro = %s, ventas_totales = %s
                                WHERE venta_id = %s
                            """, (fid_nuevo, fecha_nueva, tipo_nuevo, monto_nuevo, selected_id))
                            conn.commit()
                            st.success("✅ Cambios guardados correctamente")

                            registrar_log(
                                st.session_state["usuario"],
                                "MODIFICACION_VENTA",
                                f"Modificó venta ID {selected_id}: farmacia={farmacia_nuevo}, fecha={fecha_nueva}, tipo={tipo_nuevo}, monto={monto_nuevo}"
                            )
                        except Exception as e:
                            conn.rollback()
                            st.error(e)

        with col2:
            if st.button("❌ Eliminar registro"):
                try:
                    cursor.execute("DELETE FROM ventas WHERE venta_id = %s", (selected_id,))
                    conn.commit()
                    st.success("🗑 Registro eliminado correctamente")

                    registrar_log(
                        st.session_state["usuario"],
                        "ELIMINACION_VENTA",
                        f"Eliminó venta ID {selected_id}"
                    )
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






