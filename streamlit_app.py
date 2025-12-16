import streamlit as st

st.set_page_config(
    page_title="Sistema Farmacéutico",
    layout="wide"
)

st.title("🏥 Sistema de Ventas Farmacéuticas")

st.markdown("""
Este sistema permite:

- Registrar ventas diarias, semanales y mensuales
- Visualizar indicadores clave por farmacia
- Analizar tendencias de ventas
""")

st.info("Usa el menú lateral para navegar.")
