import streamlit as st
import pandas as pd

from utils.conexionASupabase import get_connection


st.set_page_config(
    page_title="Administración Facturas",
    layout="wide"
)

st.title("🧾 Administración de Facturas")


conn=get_connection()
cursor=conn.cursor()



if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")



tab1,tab2,tab3,tab4 = st.tabs([

"📋 Facturas",

"➕ Agregar Factura",

"🏭 Proveedores",

"📊 Estadísticas"

])
