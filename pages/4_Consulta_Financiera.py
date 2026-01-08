import streamlit as st
import pandas as pd

st.title("📄 Consulta Financiera")

st.caption(
    "Consulta detallada de **ventas y gastos**, con búsqueda, filtros y paginación."
)

# ===============================
# TABS
# ===============================
tab_ventas, tab_gastos, tab_resumen = st.tabs(
    ["🟢 Ventas", "🔴 Gastos", "🔵 Resumen"]
)

# ======================================================
# 🟢 TAB VENTAS
# ======================================================
with tab_ventas:
    st.subheader("🟢 Ventas registradas")

    # -------- Barra de herramientas
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        busqueda_venta = st.text_input(
            "🔍 Buscar por farmacia",
            placeholder="Ej. Farmacia Matías"
        )

    with col2:
        page_size_v = st.selectbox(
            "Registros por página",
            [10, 20, 50],
            key="ventas_page_size"
        )

    with col3:
        st.metric(
            "Total visible",
            f"${df_ventas_filt['ventas_totales'].sum():,.0f}"
        )

    # -------- Filtro de búsqueda
    df_v = df_ventas_filt.copy()

    if busqueda_venta:
        df_v = df_v[
            df_v["farmacia"]
            .str.contains(busqueda_venta, case=False, na=False)
        ]

    # -------- Orden lógico
    df_v = df_v.sort_values("fecha", ascending=False)

    # -------- Paginación
    total_rows = len(df_v)
    total_pages = max(1, (total_rows - 1) // page_size_v + 1)

    page_v = st.number_input(
        "Página",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key="ventas_page"
    )

    start = (page_v - 1) * page_size_v
    end = start + page_size_v

    # -------- Tabla
    st.dataframe(
        df_v.iloc[start:end],
        use_container_width=True,
        hide_index=True
    )

    st.caption(f"Página {page_v} de {total_pages}")

# ======================================================
# 🔴 TAB GASTOS
# ======================================================
with tab_gastos:
    st.subheader("🔴 Gastos registrados")

    # -------- Barra de herramientas
    c1, c2, c3 = st.columns([2, 1, 1])

    with c1:
        buscar_desc = st.text_input(
            "🔍 Buscar en descripción",
            placeholder="Ej. Luz, renta, proveedor..."
        )

    with c2:
        categorias = (
            ["Todas"]
            + sorted(df_gastos_filt["categoria"].dropna().unique())
        )
        categoria_sel = st.selectbox("Categoría", categorias)

    with c3:
        page_size_g = st.selectbox(
            "Registros por página",
            [10, 20, 50],
            key="gastos_page_size"
        )

    # -------- Filtros
    df_g = df_gastos_filt.copy()

    if buscar_desc:
        df_g = df_g[
            df_g["descripcion"]
            .str.contains(buscar_desc, case=False, na=False)
        ]

    if categoria_sel != "Todas":
        df_g = df_g[df_g["categoria"] == categoria_sel]

    # -------- Orden lógico
    df_g = df_g.sort_values("fecha", ascending=False)

    # -------- Paginación
    total_rows = len(df_g)
    total_pages = max(1, (total_rows - 1) // page_size_g + 1)

    page_g = st.number_input(
        "Página",
        min_value=1,
        max_value=total_pages,
        value=1,
        step=1,
        key="gastos_page"
    )

    start = (page_g - 1) * page_size_g
    end = start + page_size_g

    # -------- Tabla
    st.dataframe(
        df_g.iloc[start:end],
        use_container_width=True,
        hide_index=True
    )

    st.metric(
        "Total gastos visibles",
        f"${df_g['monto'].sum():,.2f}"
    )

    st.caption(f"Página {page_g} de {total_pages}")

# ======================================================
# 🔵 TAB RESUMEN
# ======================================================
with tab_resumen:
    st.subheader("🔵 Resumen financiero")

    ventas_total = df_ventas_filt["ventas_totales"].sum()
    gastos_total = df_gastos_filt["monto"].sum()
    utilidad = ventas_total - gastos_total

    st.markdown(
        f"""
        ### 📊 Totales del periodo seleccionado

        - 🟢 **Ventas totales:** ${ventas_total:,.2f}
        - 🔴 **Gastos totales:** ${gastos_total:,.2f}
        - 🔵 **Utilidad:** ${utilidad:,.2f}
        """
    )

    st.info(
        "Este resumen sirve como referencia rápida. "
        "El análisis principal se realiza en el Dashboard."
    )
