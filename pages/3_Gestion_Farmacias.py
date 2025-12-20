import streamlit as st
import pandas as pd
from utils.conexionASupabase import get_connection

st.set_page_config(page_title="Gestión de Farmacias", layout="wide")
st.title("🏥 Gestión de Farmacias")

conn = get_connection()
cursor = conn.cursor()

st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)


# Bloquear acceso si no hay sesión
if "usuario" not in st.session_state:
    st.switch_page("login.py")
# ---------------------------------
# CARGAR FARMACIAS
# ---------------------------------
df_farmacias = pd.read_sql(
    "SELECT farmacia_id, nombre, ciudad FROM farmacias ORDER BY nombre;",
    conn
)

# =================================
# 1️⃣ REGISTRO DE NUEVA FARMACIA
# =================================
st.subheader("➕ Registrar nueva farmacia")

with st.form("form_nueva_farmacia", clear_on_submit=True):
    nombre = st.text_input("Nombre de la farmacia")
    ciudad = st.text_input("Ciudad")

    submitted = st.form_submit_button("💾 Guardar farmacia")

    if submitted:
        if not nombre.strip() or not ciudad.strip():
            st.error("❌ Nombre y ciudad son obligatorios.")
        else:
            try:
                cursor.execute(
                    """
                    INSERT INTO farmacias (nombre, ciudad)
                    VALUES (%s, %s)
                    """,
                    (nombre.strip(), ciudad.strip())
                )
                conn.commit()
                st.success("✅ Farmacia registrada correctamente")
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar: {e}")

st.divider()

# =================================
# 2️⃣ LISTADO + EDICIÓN / ELIMINACIÓN
# =================================
st.subheader("📋 Farmacias registradas")

if df_farmacias.empty:
    st.info("No hay farmacias registradas.")
else:
    mostrar = st.radio(
        "Mostrar",
        ["Primeros 20", "Primeros 100", "Todas"],
        horizontal=True
    )

    if mostrar == "Primeros 20":
        df_view = df_farmacias.head(20)
    elif mostrar == "Primeros 100":
        df_view = df_farmacias.head(100)
    else:
        df_view = df_farmacias

    for _, row in df_view.iterrows():
        with st.expander(f"🏪 {row['nombre']} ({row['ciudad']})"):

            col1, col2 = st.columns(2)

            nuevo_nombre = col1.text_input(
                "Nombre",
                value=row["nombre"],
                key=f"nombre_{row['farmacia_id']}"
            )

            nueva_ciudad = col2.text_input(
                "Ciudad",
                value=row["ciudad"],
                key=f"ciudad_{row['farmacia_id']}"
            )

            c1, c2 = st.columns(2)

            if c1.button("✏️ Actualizar", key=f"update_{row['farmacia_id']}"):
                try:
                    cursor.execute(
                        """
                        UPDATE farmacias
                        SET nombre = %s, ciudad = %s
                        WHERE farmacia_id = %s
                        """,
                        (nuevo_nombre.strip(), nueva_ciudad.strip(), row["farmacia_id"])
                    )
                    conn.commit()
                    st.success("✅ Farmacia actualizada")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al actualizar: {e}")

            if c2.button("🗑 Eliminar", key=f"delete_{row['farmacia_id']}"):
                try:
                    # ⚠️ Validación: evitar eliminar farmacias con ventas
                    cursor.execute(
                        "SELECT COUNT(*) FROM ventas WHERE farmacia_id = %s",
                        (row["farmacia_id"],)
                    )
                    total_ventas = cursor.fetchone()[0]

                    if total_ventas > 0:
                        st.warning(
                            "⚠️ No se puede eliminar esta farmacia porque tiene ventas registradas."
                        )
                    else:
                        cursor.execute(
                            "DELETE FROM farmacias WHERE farmacia_id = %s",
                            (row["farmacia_id"],)
                        )
                        conn.commit()
                        st.success("🗑 Farmacia eliminada")
                        st.rerun()

                except Exception as e:
                    st.error(f"Error al eliminar: {e}")

cursor.close()
conn.close()
