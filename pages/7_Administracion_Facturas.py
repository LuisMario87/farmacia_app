import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import plotly.express as px

from datetime import date, timedelta
from html import escape

from utils.conexionASupabase import get_connection
from utils.logger import registrar_log


# ===============================
# SEGURIDAD
# ===============================

st.set_page_config(
    page_title="Administración Facturas",
    layout="wide"
)

if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")

rol_usuario = st.session_state["usuario"]["rol"].strip().lower()

roles_permitidos = ["admin", "empleado"]

if rol_usuario not in roles_permitidos:
    st.error("No tienes permisos para esta sección")
    st.stop()


st.title("🧾 Administración de Facturas")


conn=get_connection()
cursor=conn.cursor()



if "usuario" not in st.session_state:
    st.switch_page("streamlit_app.py")



tab1, tab2, tab3, tab4 = st.tabs([
    "Facturas",
    "Agregar Factura",
    "Proveedores",
    "Estadísticas"
])

# ----------------------------
# GESTIÓN DE FACTURAS
# ----------------------------

with tab1:

    st.subheader("Panel de facturas")

    # ----------------------------
    # FUNCIONES AUXILIARES
    # ----------------------------

    def limpiar_texto_factura(valor):

        if pd.isna(valor) or valor is None or str(valor).strip() == "":
            return "-"

        return str(valor)

    def formatear_fecha(valor):

        if pd.isna(valor) or valor is None:
            return "-"

        try:
            return valor.strftime("%d/%m/%Y")
        except Exception:
            return str(valor)

    def formatear_monto(valor):

        if pd.isna(valor) or valor is None:
            return "$0.00"

        return f"${float(valor):,.2f}"

    # ----------------------------
    # FILTROS DE CARGA
    # ----------------------------

    st.markdown("### Búsqueda de facturas")

    df_proveedores_filtro = pd.read_sql("""
        SELECT DISTINCT
            p.nombre AS proveedor
        FROM facturas f
        LEFT JOIN proveedores p
            ON f.proveedor_id = p.proveedor_id
        WHERE p.nombre IS NOT NULL
        ORDER BY p.nombre ASC
    """, conn)

    df_anios_filtro = pd.read_sql("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha_factura)::INT AS anio
        FROM facturas
        WHERE fecha_factura IS NOT NULL
        ORDER BY anio DESC
    """, conn)

    proveedores_filtro = (
        ["Todos"] +
        df_proveedores_filtro["proveedor"].dropna().tolist()
    )

    anios_filtro = (
        ["Todos"] +
        df_anios_filtro["anio"].dropna().astype(int).tolist()
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        filtro_proveedor_sql = st.selectbox(
            "Proveedor",
            proveedores_filtro,
            key="filtro_proveedor_sql_tab1"
        )

    with col2:

        filtro_estatus_sql = st.selectbox(
            "Estatus",
            [
                "PENDIENTE",
                "Todos",
                "PAGADA",
                "CANCELADA"
            ],
            key="filtro_estatus_sql_tab1"
        )

    with col3:

        filtro_anio_sql = st.selectbox(
            "Año",
            anios_filtro,
            key="filtro_anio_sql_tab1"
        )

    with col4:

        filtro_mes_sql = st.selectbox(
            "Mes",
            [
                "Todos",
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Septiembre",
                "Octubre",
                "Noviembre",
                "Diciembre"
            ],
            key="filtro_mes_sql_tab1"
        )

    col1, col2, col3 = st.columns(3)

    with col1:

        filtro_vencimiento_sql = st.selectbox(
            "Vencimiento",
            [
                "Todos",
                "Vencidas",
                "Vencen en 7 días",
                "En tiempo"
            ],
            key="filtro_vencimiento_sql_tab1"
        )

    with col2:

        buscar_folio_sql = st.text_input(
            "Buscar folio",
            placeholder="Ej. F12345",
            key="buscar_folio_sql_tab1"
        )

    with col3:

        registros_por_pagina = st.selectbox(
            "Registros por página",
            [10, 25, 50],
            index=1,
            key="registros_por_pagina_tab1"
        )

    # ----------------------------
    # CONSTRUIR WHERE SQL
    # ----------------------------

    meses_map = {
        "Enero": 1,
        "Febrero": 2,
        "Marzo": 3,
        "Abril": 4,
        "Mayo": 5,
        "Junio": 6,
        "Julio": 7,
        "Agosto": 8,
        "Septiembre": 9,
        "Octubre": 10,
        "Noviembre": 11,
        "Diciembre": 12
    }

    condiciones_sql = []
    parametros_sql = []

    if filtro_proveedor_sql != "Todos":

        condiciones_sql.append("p.nombre = %s")
        parametros_sql.append(filtro_proveedor_sql)

    if filtro_estatus_sql != "Todos":

        condiciones_sql.append("f.estatus = %s")
        parametros_sql.append(filtro_estatus_sql)

    if filtro_anio_sql != "Todos":

        condiciones_sql.append("EXTRACT(YEAR FROM f.fecha_factura)::INT = %s")
        parametros_sql.append(int(filtro_anio_sql))

    if filtro_mes_sql != "Todos":

        condiciones_sql.append("EXTRACT(MONTH FROM f.fecha_factura)::INT = %s")
        parametros_sql.append(meses_map[filtro_mes_sql])

    if buscar_folio_sql.strip():

        condiciones_sql.append("f.folio ILIKE %s")
        parametros_sql.append(f"%{buscar_folio_sql.strip()}%")

    if filtro_vencimiento_sql == "Vencidas":

        condiciones_sql.append("f.estatus = 'PENDIENTE'")
        condiciones_sql.append("f.fecha_vencimiento < CURRENT_DATE")

    elif filtro_vencimiento_sql == "Vencen en 7 días":

        condiciones_sql.append("f.estatus = 'PENDIENTE'")
        condiciones_sql.append("""
            f.fecha_vencimiento >= CURRENT_DATE
            AND f.fecha_vencimiento <= CURRENT_DATE + INTERVAL '7 days'
        """)

    elif filtro_vencimiento_sql == "En tiempo":

        condiciones_sql.append("f.estatus = 'PENDIENTE'")
        condiciones_sql.append("f.fecha_vencimiento > CURRENT_DATE + INTERVAL '7 days'")

    if condiciones_sql:

        where_sql = "WHERE " + " AND ".join(condiciones_sql)

    else:

        where_sql = ""

    # ----------------------------
    # CONTAR REGISTROS FILTRADOS
    # ----------------------------

    query_total_facturas = f"""
        SELECT COUNT(*) AS total
        FROM facturas f
        LEFT JOIN proveedores p
            ON f.proveedor_id = p.proveedor_id
        {where_sql}
    """

    total_registros = pd.read_sql(
        query_total_facturas,
        conn,
        params=parametros_sql
    )["total"].iloc[0]

    total_registros = int(total_registros)

    total_paginas = max(
        1,
        (total_registros + int(registros_por_pagina) - 1) // int(registros_por_pagina)
    )

    if "pagina_facturas_tab1" not in st.session_state:
        st.session_state["pagina_facturas_tab1"] = 1

    if st.session_state["pagina_facturas_tab1"] > total_paginas:
        st.session_state["pagina_facturas_tab1"] = 1

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:

        pagina_actual = st.number_input(
            "Página",
            min_value=1,
            max_value=total_paginas,
            value=st.session_state["pagina_facturas_tab1"],
            step=1,
            key="pagina_facturas_tab1"
        )

    with col2:

        st.metric(
            "Total resultados",
            total_registros
        )

    with col3:

        st.caption(
            f"Página {pagina_actual} de {total_paginas}. "
            f"Mostrando máximo {registros_por_pagina} facturas por página."
        )

    offset = (int(pagina_actual) - 1) * int(registros_por_pagina)

    # ----------------------------
    # KPIS GENERALES DE LA BÚSQUEDA
    # ----------------------------

    query_kpis = f"""
        SELECT
            COALESCE(SUM(CASE WHEN f.estatus = 'PENDIENTE' THEN f.monto ELSE 0 END), 0) AS saldo_pendiente,
            COUNT(*) FILTER (WHERE f.estatus = 'PENDIENTE') AS facturas_pendientes,
            COUNT(*) FILTER (
                WHERE f.estatus = 'PENDIENTE'
                AND f.fecha_vencimiento < CURRENT_DATE
            ) AS facturas_vencidas,
            COUNT(*) FILTER (
                WHERE f.estatus = 'PENDIENTE'
                AND f.fecha_vencimiento >= CURRENT_DATE
                AND f.fecha_vencimiento <= CURRENT_DATE + INTERVAL '7 days'
            ) AS facturas_proximas
        FROM facturas f
        LEFT JOIN proveedores p
            ON f.proveedor_id = p.proveedor_id
        {where_sql}
    """

    df_kpis = pd.read_sql(
        query_kpis,
        conn,
        params=parametros_sql
    )

    saldo_pendiente = float(df_kpis["saldo_pendiente"].iloc[0])
    facturas_pendientes = int(df_kpis["facturas_pendientes"].iloc[0])
    facturas_vencidas = int(df_kpis["facturas_vencidas"].iloc[0])
    facturas_proximas = int(df_kpis["facturas_proximas"].iloc[0])

    # ----------------------------
    # CONSULTA PAGINADA DE FACTURAS
    # ----------------------------

    query_facturas = f"""
        SELECT
            f.factura_id,
            p.nombre AS proveedor,
            f.folio,
            f.fecha_factura,
            f.dias_credito,
            f.fecha_vencimiento,
            f.monto,
            f.estatus,
            f.observaciones,
            f.created_at
        FROM facturas f
        LEFT JOIN proveedores p
            ON f.proveedor_id = p.proveedor_id
        {where_sql}
        ORDER BY
            CASE
                WHEN f.estatus = 'PENDIENTE' THEN 0
                WHEN f.estatus = 'PAGADA' THEN 1
                WHEN f.estatus = 'CANCELADA' THEN 2
                ELSE 3
            END,
            f.fecha_vencimiento ASC NULLS LAST,
            f.created_at DESC
        LIMIT %s
        OFFSET %s
    """

    parametros_facturas = parametros_sql.copy()

    parametros_facturas.extend([
        int(registros_por_pagina),
        int(offset)
    ])

    df_facturas = pd.read_sql(
        query_facturas,
        conn,
        params=parametros_facturas
    )

    # ----------------------------
    # KPIS
    # ----------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:

        st.metric(
            "Pendiente por pagar",
            f"${saldo_pendiente:,.2f}"
        )

    with col2:

        st.metric(
            "Facturas pendientes",
            facturas_pendientes
        )

    with col3:

        st.metric(
            "Facturas vencidas",
            facturas_vencidas
        )

    with col4:

        st.metric(
            "Vencen en 7 días",
            facturas_proximas
        )

    st.divider()

    if df_facturas.empty:

        st.info("No hay facturas que coincidan con los filtros seleccionados.")

    else:

        # ----------------------------
        # LIMPIEZA DE FECHAS
        # ----------------------------

        df_facturas["fecha_factura"] = pd.to_datetime(
            df_facturas["fecha_factura"],
            errors="coerce"
        ).dt.date

        df_facturas["fecha_vencimiento"] = pd.to_datetime(
            df_facturas["fecha_vencimiento"],
            errors="coerce"
        ).dt.date

        df_facturas["monto"] = df_facturas["monto"].astype(float)

        hoy = date.today()

        df_facturas["dias_restantes"] = df_facturas["fecha_vencimiento"].apply(
            lambda fecha: (fecha - hoy).days if pd.notnull(fecha) else None
        )

        df_filtrado = df_facturas.copy()

        # ----------------------------
        # TABLA VISUAL DE FACTURAS
        # ----------------------------

        st.markdown("### Facturas registradas")

        def obtener_estatus_visual(fila):

            estatus = fila["estatus"]
            dias = fila["dias_restantes"]

            if estatus == "CANCELADA":
                return {
                    "texto": "CANCELADA",
                    "detalle": "Factura cancelada",
                    "clase_badge": "badge-cancelada",
                    "clase_fila": "fila-cancelada"
                }

            if estatus == "PAGADA":
                return {
                    "texto": "PAGADA",
                    "detalle": "Factura liquidada",
                    "clase_badge": "badge-pagada",
                    "clase_fila": "fila-pagada"
                }

            if pd.isna(dias):
                return {
                    "texto": "SIN FECHA",
                    "detalle": "Sin vencimiento",
                    "clase_badge": "badge-cancelada",
                    "clase_fila": "fila-cancelada"
                }

            dias = int(dias)

            if dias < 0:
                return {
                    "texto": "VENCIDA",
                    "detalle": f"Hace {abs(dias)} días",
                    "clase_badge": "badge-rojo",
                    "clase_fila": "fila-roja"
                }

            if dias == 0:
                return {
                    "texto": "VENCE HOY",
                    "detalle": "Pagar hoy",
                    "clase_badge": "badge-naranja",
                    "clase_fila": "fila-naranja"
                }

            if dias <= 7:
                return {
                    "texto": "POR VENCER",
                    "detalle": f"Faltan {dias} días",
                    "clase_badge": "badge-naranja",
                    "clase_fila": "fila-naranja"
                }

            return {
                "texto": "EN TIEMPO",
                "detalle": f"Faltan {dias} días",
                "clase_badge": "badge-verde",
                "clase_fila": "fila-verde"
            }

        estilos_tabla = """
        <style>
            body {
                margin: 0;
                padding: 0;
                background: transparent;
                font-family: Arial, sans-serif;
            }

            .tabla-facturas-contenedor {
                width: 100%;
                overflow-x: auto;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
                background: #ffffff;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            }

            .tabla-facturas {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                font-size: 14px;
            }

            .tabla-facturas thead th {
                background: #f8fafc;
                color: #334155;
                text-align: left;
                padding: 15px 16px;
                font-weight: 700;
                border-bottom: 1px solid #e5e7eb;
                white-space: nowrap;
            }

            .tabla-facturas tbody td {
                padding: 15px 16px;
                border-bottom: 1px solid #f1f5f9;
                color: #1f2937;
                vertical-align: middle;
                background: #ffffff;
            }

            .tabla-facturas tbody tr:last-child td {
                border-bottom: none;
            }

            .tabla-facturas tbody tr:hover td {
                background: #f8fafc;
            }

            .proveedor-texto {
                font-weight: 700;
                color: #111827;
            }

            .folio-texto {
                font-weight: 700;
                color: #334155;
                background: #f1f5f9;
                padding: 5px 9px;
                border-radius: 8px;
                display: inline-block;
            }

            .fecha-texto {
                color: #475569;
                white-space: nowrap;
                font-weight: 500;
            }

            .monto-texto {
                font-weight: 800;
                color: #111827;
                text-align: right;
                white-space: nowrap;
            }

            .observaciones-texto {
                color: #64748b;
                max-width: 280px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                display: inline-block;
            }

            .badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-width: 112px;
                padding: 7px 11px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.35px;
                text-align: center;
                white-space: nowrap;
            }

            .badge-verde {
                background: #dcfce7;
                color: #166534;
                border: 1px solid #86efac;
            }

            .badge-naranja {
                background: #ffedd5;
                color: #9a3412;
                border: 1px solid #fdba74;
            }

            .badge-rojo {
                background: #fee2e2;
                color: #991b1b;
                border: 1px solid #fca5a5;
            }

            .badge-cancelada {
                background: #ffffff;
                color: #64748b;
                border: 1px solid #cbd5e1;
            }

            .badge-pagada {
                background: #e0f2fe;
                color: #075985;
                border: 1px solid #7dd3fc;
            }

            .estatus-detalle {
                display: block;
                margin-top: 5px;
                font-size: 12px;
                color: #64748b;
                font-weight: 500;
            }

            .fila-verde td:first-child {
                border-left: 6px solid #22c55e;
            }

            .fila-naranja td:first-child {
                border-left: 6px solid #f97316;
            }

            .fila-roja td:first-child {
                border-left: 6px solid #ef4444;
            }

            .fila-cancelada td:first-child {
                border-left: 6px solid #e5e7eb;
            }

            .fila-pagada td:first-child {
                border-left: 6px solid #38bdf8;
            }
        </style>
        """

        filas_html = ""

        for _, fila in df_filtrado.iterrows():

            visual = obtener_estatus_visual(fila)

            proveedor_html = escape(limpiar_texto_factura(fila["proveedor"]))
            folio_html = escape(limpiar_texto_factura(fila["folio"]))
            observaciones_html = escape(limpiar_texto_factura(fila["observaciones"]))

            filas_html += f"""
                <tr class="{visual['clase_fila']}">
                    <td>
                        <span class="proveedor-texto">{proveedor_html}</span>
                    </td>
                    <td>
                        <span class="folio-texto">{folio_html}</span>
                    </td>
                    <td>
                        <span class="fecha-texto">{formatear_fecha(fila["fecha_factura"])}</span>
                    </td>
                    <td>
                        <span class="fecha-texto">{formatear_fecha(fila["fecha_vencimiento"])}</span>
                    </td>
                    <td>
                        <span class="badge {visual['clase_badge']}">
                            {visual['texto']}
                        </span>
                        <span class="estatus-detalle">
                            {visual['detalle']}
                        </span>
                    </td>
                    <td class="monto-texto">
                        {formatear_monto(fila["monto"])}
                    </td>
                    <td>
                        <span class="observaciones-texto" title="{observaciones_html}">
                            {observaciones_html}
                        </span>
                    </td>
                </tr>
            """

        tabla_html = f"""
        {estilos_tabla}

        <div class="tabla-facturas-contenedor">
            <table class="tabla-facturas">
                <thead>
                    <tr>
                        <th>Proveedor</th>
                        <th>Folio</th>
                        <th>Fecha factura</th>
                        <th>Vencimiento</th>
                        <th>Estatus</th>
                        <th>Monto</th>
                        <th>Observaciones</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_html}
                </tbody>
            </table>
        </div>
        """

        altura_tabla = min(
            750,
            130 + (len(df_filtrado) * 78)
        )

        components.html(
            tabla_html,
            height=altura_tabla,
            scrolling=True
        )

        st.caption(
            f"Facturas mostradas en esta página: {len(df_filtrado)} de {total_registros} resultados."
        )

        st.divider()

        # ----------------------------
        # ACCIONES SOBRE FACTURAS
        # ----------------------------

        with st.expander("Acciones sobre facturas", expanded=False):

            opciones_facturas = {}

            for _, fila in df_filtrado.iterrows():

                etiqueta = (
                    f"{limpiar_texto_factura(fila['proveedor'])} | "
                    f"Folio: {limpiar_texto_factura(fila['folio'])} | "
                    f"{limpiar_texto_factura(fila['estatus'])} | "
                    f"Vence: {formatear_fecha(fila['fecha_vencimiento'])} | "
                    f"{formatear_monto(fila['monto'])}"
                )

                opciones_facturas[etiqueta] = int(fila["factura_id"])

            factura_sel = st.selectbox(
                "Selecciona una factura",
                list(opciones_facturas.keys()),
                key="select_factura_administrar"
            )

            factura_id_sel = opciones_facturas[factura_sel]

            factura_data = df_facturas[
                df_facturas["factura_id"] == factura_id_sel
            ].iloc[0]

            estatus_actual = factura_data["estatus"]
            dias_actuales = factura_data["dias_restantes"]

            if pd.isna(dias_actuales):
                dias_actuales = 0
            else:
                dias_actuales = int(dias_actuales)

            if estatus_actual == "CANCELADA":
                color_estado = "#64748b"
                fondo_estado = "#ffffff"
                borde_estado = "#cbd5e1"
                texto_estado = "CANCELADA"

            elif estatus_actual == "PAGADA":
                color_estado = "#075985"
                fondo_estado = "#e0f2fe"
                borde_estado = "#7dd3fc"
                texto_estado = "PAGADA"

            elif dias_actuales < 0:
                color_estado = "#991b1b"
                fondo_estado = "#fee2e2"
                borde_estado = "#fca5a5"
                texto_estado = "VENCIDA"

            elif dias_actuales <= 7:
                color_estado = "#9a3412"
                fondo_estado = "#ffedd5"
                borde_estado = "#fdba74"
                texto_estado = "POR VENCER"

            else:
                color_estado = "#166534"
                fondo_estado = "#dcfce7"
                borde_estado = "#86efac"
                texto_estado = "EN TIEMPO"

            proveedor_resumen = escape(limpiar_texto_factura(factura_data["proveedor"]))
            folio_resumen = escape(limpiar_texto_factura(factura_data["folio"]))
            monto_resumen = float(factura_data["monto"])

            resumen_html = f"""
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: Arial, sans-serif;
                }}

                .card-factura {{
                    border: 1px solid #e5e7eb;
                    border-radius: 16px;
                    padding: 20px 22px;
                    background: #ffffff;
                    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
                }}

                .card-contenido {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 16px;
                    flex-wrap: wrap;
                }}

                .label {{
                    font-size: 13px;
                    color: #64748b;
                    font-weight: 600;
                    margin-bottom: 5px;
                }}

                .proveedor {{
                    font-size: 21px;
                    color: #111827;
                    font-weight: 800;
                }}

                .folio {{
                    font-size: 14px;
                    color: #475569;
                    margin-top: 5px;
                }}

                .lado-derecho {{
                    text-align: right;
                }}

                .badge-estado {{
                    display: inline-block;
                    background: {fondo_estado};
                    color: {color_estado};
                    border: 1px solid {borde_estado};
                    border-radius: 999px;
                    padding: 7px 14px;
                    font-size: 12px;
                    font-weight: 800;
                    letter-spacing: 0.3px;
                }}

                .monto {{
                    font-size: 24px;
                    color: #111827;
                    font-weight: 800;
                    margin-top: 10px;
                }}
            </style>

            <div class="card-factura">
                <div class="card-contenido">
                    <div>
                        <div class="label">Factura seleccionada</div>
                        <div class="proveedor">{proveedor_resumen}</div>
                        <div class="folio">Folio: <strong>{folio_resumen}</strong></div>
                    </div>

                    <div class="lado-derecho">
                        <span class="badge-estado">{texto_estado}</span>
                        <div class="monto">${monto_resumen:,.2f}</div>
                    </div>
                </div>
            </div>
            """

            components.html(
                resumen_html,
                height=150,
                scrolling=False
            )

            st.markdown("#### Editar datos de la factura")

            # Este sufijo hace que cada factura tenga sus propios campos
            # y evita que Streamlit conserve valores de otra factura.
            key_factura = f"factura_{factura_id_sel}"

            dias_credito_actual = (
                0 if pd.isna(factura_data["dias_credito"])
                else int(factura_data["dias_credito"])
            )

            estatus_opciones = ["PENDIENTE", "PAGADA", "CANCELADA"]

            if factura_data["estatus"] in estatus_opciones:
                index_estatus = estatus_opciones.index(factura_data["estatus"])
            else:
                index_estatus = 0

            fecha_factura_actual = (
                date.today()
                if pd.isna(factura_data["fecha_factura"])
                else factura_data["fecha_factura"]
            )

            fecha_vencimiento_actual = (
                date.today()
                if pd.isna(factura_data["fecha_vencimiento"])
                else factura_data["fecha_vencimiento"]
            )

            observaciones_actuales = (
                "" if pd.isna(factura_data["observaciones"])
                else str(factura_data["observaciones"])
            )

            with st.form(f"form_editar_factura_{key_factura}"):

                col1, col2 = st.columns(2)

                with col1:

                    folio_edit = st.text_input(
                        "Folio",
                        value=str(factura_data["folio"]),
                        key=f"folio_edit_{key_factura}"
                    )

                    fecha_factura_edit = st.date_input(
                        "Fecha de factura",
                        value=fecha_factura_actual,
                        key=f"fecha_factura_edit_{key_factura}"
                    )

                    dias_credito_edit = st.number_input(
                        "Días de crédito",
                        min_value=0,
                        max_value=365,
                        value=dias_credito_actual,
                        key=f"dias_credito_edit_{key_factura}"
                    )

                with col2:

                    fecha_vencimiento_edit = st.date_input(
                        "Fecha de vencimiento",
                        value=fecha_vencimiento_actual,
                        key=f"fecha_vencimiento_edit_{key_factura}"
                    )

                    monto_edit = st.number_input(
                        "Monto",
                        min_value=0.0,
                        step=100.0,
                        format="%.2f",
                        value=float(factura_data["monto"]),
                        key=f"monto_edit_{key_factura}"
                    )

                    estatus_edit = st.selectbox(
                        "Estatus",
                        estatus_opciones,
                        index=index_estatus,
                        key=f"estatus_edit_{key_factura}"
                    )

                recalcular_vencimiento = st.checkbox(
                    "Recalcular vencimiento automáticamente usando fecha de factura + días de crédito",
                    value=False,
                    key=f"recalcular_vencimiento_edit_{key_factura}"
                )

                observaciones_edit = st.text_area(
                    "Observaciones",
                    value=observaciones_actuales,
                    key=f"observaciones_edit_{key_factura}"
                )

                guardar_cambios_factura = st.form_submit_button(
                    "Guardar cambios de factura",
                    use_container_width=True
                )

            if guardar_cambios_factura:

                if folio_edit.strip() == "":

                    st.error("El folio de la factura es obligatorio.")
                    st.stop()

                if monto_edit <= 0:

                    st.error("El monto debe ser mayor a 0.")
                    st.stop()

                if recalcular_vencimiento:

                    fecha_vencimiento_final = (
                        fecha_factura_edit +
                        timedelta(days=int(dias_credito_edit))
                    )

                else:

                    fecha_vencimiento_final = fecha_vencimiento_edit

                try:

                    cursor.execute("""
                        SELECT proveedor_id
                        FROM facturas
                        WHERE factura_id = %s
                    """, (
                        factura_id_sel,
                    ))

                    proveedor_id_actual = cursor.fetchone()[0]

                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM facturas
                        WHERE proveedor_id = %s
                        AND UPPER(folio) = UPPER(%s)
                        AND factura_id <> %s
                    """, (
                        proveedor_id_actual,
                        folio_edit.strip(),
                        factura_id_sel
                    ))

                    existe_folio = cursor.fetchone()[0]

                    if existe_folio > 0:

                        st.error("Ya existe otra factura con ese folio para este proveedor.")
                        st.stop()

                    cursor.execute("""
                        UPDATE facturas
                        SET
                            folio = %s,
                            fecha_factura = %s,
                            dias_credito = %s,
                            fecha_vencimiento = %s,
                            monto = %s,
                            estatus = %s,
                            observaciones = %s
                        WHERE factura_id = %s
                    """, (
                        folio_edit.strip(),
                        fecha_factura_edit,
                        int(dias_credito_edit),
                        fecha_vencimiento_final,
                        float(monto_edit),
                        estatus_edit,
                        observaciones_edit.strip(),
                        factura_id_sel
                    ))

                    conn.commit()

                    registrar_log(
                        st.session_state["usuario"],
                        "MODIFICACION_FACTURA",
                        f"Modificó la factura ID {factura_id_sel}"
                    )

                    st.success("Factura actualizada correctamente.")

                    st.rerun()

                except Exception as e:

                    conn.rollback()

                    st.error(e)


            st.divider()

            st.markdown("#### Acciones rápidas")

            col1, col2, col3 = st.columns(3)

            with col1:

                if st.button(
                    "Marcar como pagada",
                    use_container_width=True,
                    disabled=estatus_actual == "PAGADA",
                    key="btn_marcar_pagada"
                ):

                    try:

                        cursor.execute("""
                            UPDATE facturas
                            SET estatus = 'PAGADA'
                            WHERE factura_id = %s
                        """, (
                            factura_id_sel,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "FACTURA_PAGADA",
                            f"Marcó como pagada la factura ID {factura_id_sel}"
                        )

                        st.success("Factura marcada como pagada correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)

            with col2:

                if st.button(
                    "Cancelar factura",
                    use_container_width=True,
                    disabled=estatus_actual == "CANCELADA",
                    key="btn_cancelar_factura"
                ):

                    try:

                        cursor.execute("""
                            UPDATE facturas
                            SET estatus = 'CANCELADA'
                            WHERE factura_id = %s
                        """, (
                            factura_id_sel,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "FACTURA_CANCELADA",
                            f"Canceló la factura ID {factura_id_sel}"
                        )

                        st.success("Factura cancelada correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)

            with col3:

                if st.button(
                    "Reabrir como pendiente",
                    use_container_width=True,
                    disabled=estatus_actual == "PENDIENTE",
                    key="btn_reabrir_factura"
                ):

                    try:

                        cursor.execute("""
                            UPDATE facturas
                            SET estatus = 'PENDIENTE'
                            WHERE factura_id = %s
                        """, (
                            factura_id_sel,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "FACTURA_REABIERTA",
                            f"Reabrió como pendiente la factura ID {factura_id_sel}"
                        )

                        st.success("Factura reabierta como pendiente correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)


# ----------------------------
# GESTIÓN DE PROVEEDORES
# ----------------------------

with tab3:

    st.subheader("Gestión de proveedores")

    # ----------------------------
    # FILTROS
    # ----------------------------

    col1, col2 = st.columns([3, 1])

    with col1:

        buscar_proveedor = st.text_input(
            "Buscar proveedor",
            placeholder="Nombre, contacto, teléfono o correo...",
            key="buscar_proveedor_tab3"
        )

    with col2:

        mostrar_inactivos = st.checkbox(
            "Mostrar inactivos",
            value=False,
            key="mostrar_inactivos_tab3"
        )

    # ----------------------------
    # CONSULTA DE PROVEEDORES
    # ----------------------------

    query_proveedores = """
        SELECT
            p.proveedor_id,
            p.nombre,
            p.contacto,
            p.telefono,
            p.correo,
            p.dias_credito,
            p.estado,
            p.observaciones,
            COALESCE(m.facturas_total, 0) AS facturas_total,
            COALESCE(m.facturas_pendientes, 0) AS facturas_pendientes,
            COALESCE(m.saldo_pendiente, 0) AS saldo_pendiente,
            m.ultima_factura
        FROM proveedores p
        LEFT JOIN (
            SELECT
                proveedor_id,
                COUNT(*) AS facturas_total,
                COUNT(*) FILTER (WHERE estatus = 'PENDIENTE') AS facturas_pendientes,
                COALESCE(
                    SUM(
                        CASE
                            WHEN estatus = 'PENDIENTE' THEN monto
                            ELSE 0
                        END
                    ),
                    0
                ) AS saldo_pendiente,
                MAX(fecha_factura) AS ultima_factura
            FROM facturas
            GROUP BY proveedor_id
        ) m
            ON p.proveedor_id = m.proveedor_id
    """

    condiciones = []
    parametros = []

    if not mostrar_inactivos:

        condiciones.append("p.estado = %s")
        parametros.append("ACTIVO")

    if buscar_proveedor.strip():

        condiciones.append("""
            (
                p.nombre ILIKE %s
                OR p.contacto ILIKE %s
                OR p.telefono ILIKE %s
                OR p.correo ILIKE %s
            )
        """)

        busqueda = f"%{buscar_proveedor.strip()}%"

        parametros.extend([
            busqueda,
            busqueda,
            busqueda,
            busqueda
        ])

    if condiciones:

        query_proveedores += " WHERE " + " AND ".join(condiciones)

    query_proveedores += " ORDER BY p.nombre ASC"

    df_proveedores = pd.read_sql(
        query_proveedores,
        conn,
        params=parametros
    )

    # ----------------------------
    # KPIS DE PROVEEDORES
    # ----------------------------

    if not df_proveedores.empty:

        total_proveedores = len(df_proveedores)

        proveedores_activos = len(
            df_proveedores[
                df_proveedores["estado"] == "ACTIVO"
            ]
        )

        facturas_pendientes_total = int(
            df_proveedores["facturas_pendientes"].sum()
        )

        saldo_pendiente_total = float(
            df_proveedores["saldo_pendiente"].sum()
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:

            st.metric(
                "Proveedores mostrados",
                total_proveedores
            )

        with col2:

            st.metric(
                "Proveedores activos",
                proveedores_activos
            )

        with col3:

            st.metric(
                "Facturas pendientes",
                facturas_pendientes_total
            )

        with col4:

            st.metric(
                "Saldo pendiente",
                f"${saldo_pendiente_total:,.2f}"
            )

    else:

        st.info("No hay proveedores para mostrar con los filtros seleccionados.")

    st.divider()

    # ----------------------------
    # TABLA VISUAL DE PROVEEDORES
    # ----------------------------

    st.markdown("### Proveedores registrados")

    def formato_monto_proveedor(valor):

        if pd.isna(valor):
            return "$0.00"

        return f"${float(valor):,.2f}"

    def formato_fecha_proveedor(valor):

        if pd.isna(valor) or valor is None:
            return "-"

        try:
            return pd.to_datetime(valor).strftime("%d/%m/%Y")
        except Exception:
            return str(valor)

    def limpiar_texto(valor):

        if pd.isna(valor) or valor is None or str(valor).strip() == "":
            return "-"

        return str(valor)

    if not df_proveedores.empty:

        estilos_proveedores = """
        <style>
            body {
                margin: 0;
                padding: 0;
                background: transparent;
                font-family: Arial, sans-serif;
            }

            .tabla-proveedores-contenedor {
                width: 100%;
                overflow-x: auto;
                border-radius: 16px;
                border: 1px solid #e5e7eb;
                background: #ffffff;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            }

            .tabla-proveedores {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                font-size: 14px;
            }

            .tabla-proveedores thead th {
                background: #f8fafc;
                color: #334155;
                text-align: left;
                padding: 15px 16px;
                font-weight: 700;
                border-bottom: 1px solid #e5e7eb;
                white-space: nowrap;
            }

            .tabla-proveedores tbody td {
                padding: 15px 16px;
                border-bottom: 1px solid #f1f5f9;
                color: #1f2937;
                vertical-align: middle;
                background: #ffffff;
            }

            .tabla-proveedores tbody tr:last-child td {
                border-bottom: none;
            }

            .tabla-proveedores tbody tr:hover td {
                background: #f8fafc;
            }

            .proveedor-nombre {
                font-weight: 800;
                color: #111827;
                display: block;
            }

            .proveedor-contacto {
                color: #64748b;
                font-size: 12px;
                margin-top: 4px;
                display: block;
            }

            .texto-normal {
                color: #475569;
                font-weight: 500;
                white-space: nowrap;
            }

            .credito-badge {
                display: inline-block;
                background: #f1f5f9;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 800;
                white-space: nowrap;
            }

            .badge-activo {
                display: inline-block;
                background: #dcfce7;
                color: #166534;
                border: 1px solid #86efac;
                border-radius: 999px;
                padding: 7px 12px;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.3px;
                white-space: nowrap;
            }

            .badge-inactivo {
                display: inline-block;
                background: #ffffff;
                color: #64748b;
                border: 1px solid #cbd5e1;
                border-radius: 999px;
                padding: 7px 12px;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.3px;
                white-space: nowrap;
            }

            .pendientes-badge {
                display: inline-block;
                background: #ffedd5;
                color: #9a3412;
                border: 1px solid #fdba74;
                border-radius: 999px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 800;
                white-space: nowrap;
            }

            .saldo-texto {
                font-weight: 800;
                color: #111827;
                text-align: right;
                white-space: nowrap;
            }

            .fila-activa td:first-child {
                border-left: 6px solid #22c55e;
            }

            .fila-inactiva td:first-child {
                border-left: 6px solid #e5e7eb;
            }
        </style>
        """

        filas_proveedores_html = ""

        for _, fila in df_proveedores.iterrows():

            estado = str(fila["estado"] or "INACTIVO").upper()

            if estado == "ACTIVO":

                clase_fila = "fila-activa"
                badge_estado = '<span class="badge-activo">ACTIVO</span>'

            else:

                clase_fila = "fila-inactiva"
                badge_estado = '<span class="badge-inactivo">INACTIVO</span>'

            proveedor_html = escape(limpiar_texto(fila["nombre"]))
            contacto_html = escape(limpiar_texto(fila["contacto"]))
            telefono_html = escape(limpiar_texto(fila["telefono"]))
            correo_html = escape(limpiar_texto(fila["correo"]))

            dias_credito_html = int(
                0 if pd.isna(fila["dias_credito"]) else fila["dias_credito"]
            )

            facturas_pendientes_html = int(
                0 if pd.isna(fila["facturas_pendientes"]) else fila["facturas_pendientes"]
            )

            filas_proveedores_html += f"""
                <tr class="{clase_fila}">
                    <td>
                        <span class="proveedor-nombre">{proveedor_html}</span>
                        <span class="proveedor-contacto">Contacto: {contacto_html}</span>
                    </td>
                    <td>
                        <span class="texto-normal">{telefono_html}</span>
                    </td>
                    <td>
                        <span class="texto-normal">{correo_html}</span>
                    </td>
                    <td>
                        <span class="credito-badge">{dias_credito_html} días</span>
                    </td>
                    <td>
                        {badge_estado}
                    </td>
                    <td>
                        <span class="pendientes-badge">{facturas_pendientes_html}</span>
                    </td>
                    <td class="saldo-texto">
                        {formato_monto_proveedor(fila["saldo_pendiente"])}
                    </td>
                    <td>
                        <span class="texto-normal">{formato_fecha_proveedor(fila["ultima_factura"])}</span>
                    </td>
                </tr>
            """

        tabla_proveedores_html = f"""
        {estilos_proveedores}

        <div class="tabla-proveedores-contenedor">
            <table class="tabla-proveedores">
                <thead>
                    <tr>
                        <th>Proveedor</th>
                        <th>Teléfono</th>
                        <th>Correo</th>
                        <th>Crédito</th>
                        <th>Estado</th>
                        <th>Pendientes</th>
                        <th>Saldo pendiente</th>
                        <th>Última factura</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_proveedores_html}
                </tbody>
            </table>
        </div>
        """

        altura_proveedores = min(
            750,
            130 + (len(df_proveedores) * 78)
        )

        components.html(
            tabla_proveedores_html,
            height=altura_proveedores,
            scrolling=True
        )

        st.caption(
            f"Proveedores mostrados: {len(df_proveedores)}"
        )

    st.divider()

    # ----------------------------
    # REGISTRAR PROVEEDOR
    # ----------------------------

    with st.expander("Registrar nuevo proveedor", expanded=False):

        with st.form("form_nuevo_proveedor_tab3", clear_on_submit=True):

            nombre = st.text_input(
                "Nombre del proveedor",
                key="nuevo_proveedor_nombre"
            )

            col1, col2 = st.columns(2)

            with col1:

                contacto = st.text_input(
                    "Contacto",
                    key="nuevo_proveedor_contacto"
                )

                telefono = st.text_input(
                    "Teléfono",
                    key="nuevo_proveedor_telefono"
                )

            with col2:

                correo = st.text_input(
                    "Correo",
                    key="nuevo_proveedor_correo"
                )

                dias_credito = st.number_input(
                    "Días de crédito",
                    min_value=0,
                    max_value=365,
                    value=30,
                    key="nuevo_proveedor_dias"
                )

            observaciones = st.text_area(
                "Observaciones",
                height=90,
                key="nuevo_proveedor_observaciones"
            )

            guardar_proveedor = st.form_submit_button(
                "Guardar proveedor",
                use_container_width=True
            )

        if guardar_proveedor:

            nombre_limpio = nombre.strip()

            if nombre_limpio == "":

                st.error("El nombre del proveedor es obligatorio.")

            else:

                cursor.execute("""
                    SELECT COUNT(*)
                    FROM proveedores
                    WHERE UPPER(nombre) = UPPER(%s)
                """, (
                    nombre_limpio,
                ))

                existe = cursor.fetchone()[0]

                if existe > 0:

                    st.warning("Ya existe un proveedor con ese nombre.")

                else:

                    try:

                        cursor.execute("""
                            INSERT INTO proveedores
                            (
                                nombre,
                                contacto,
                                telefono,
                                correo,
                                dias_credito,
                                estado,
                                observaciones
                            )
                            VALUES
                            (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                'ACTIVO',
                                %s
                            )
                        """, (
                            nombre_limpio,
                            contacto.strip(),
                            telefono.strip(),
                            correo.strip(),
                            int(dias_credito),
                            observaciones.strip()
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "ALTA_PROVEEDOR",
                            f"Registró el proveedor {nombre_limpio}"
                        )

                        st.success("Proveedor registrado correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)

    # ----------------------------
    # EDITAR PROVEEDOR
    # ----------------------------

    with st.expander("Editar proveedor", expanded=False):

        if df_proveedores.empty:

            st.info("No hay proveedores disponibles para editar con los filtros actuales.")

        else:

            opciones_proveedores = {}

            for _, fila in df_proveedores.iterrows():

                etiqueta = (
                    f"{fila['nombre']} | "
                    f"{fila['estado']} | "
                    f"Pendientes: {int(fila['facturas_pendientes'])} | "
                    f"Saldo: ${float(fila['saldo_pendiente']):,.2f}"
                )

                opciones_proveedores[etiqueta] = int(fila["proveedor_id"])

            proveedor_sel = st.selectbox(
                "Selecciona un proveedor",
                list(opciones_proveedores.keys()),
                key="select_editar_proveedor_tab3"
            )

            proveedor_id = opciones_proveedores[proveedor_sel]

            proveedor_data = df_proveedores[
                df_proveedores["proveedor_id"] == proveedor_id
            ].iloc[0]

            st.markdown("#### Resumen del proveedor")

            col1, col2, col3 = st.columns(3)

            with col1:

                st.metric(
                    "Facturas pendientes",
                    int(proveedor_data["facturas_pendientes"])
                )

            with col2:

                st.metric(
                    "Saldo pendiente",
                    f"${float(proveedor_data['saldo_pendiente']):,.2f}"
                )

            with col3:

                st.metric(
                    "Facturas totales",
                    int(proveedor_data["facturas_total"])
                )

            estado_actual = str(
                proveedor_data["estado"] or "INACTIVO"
            ).upper()

            if estado_actual not in ["ACTIVO", "INACTIVO"]:
                estado_actual = "INACTIVO"

            estado_opciones = ["ACTIVO", "INACTIVO"]

            index_estado = estado_opciones.index(estado_actual)

            observaciones_actuales = (
                "" if pd.isna(proveedor_data["observaciones"])
                else str(proveedor_data["observaciones"])
            )

            with st.form("form_editar_proveedor_tab3"):

                col1, col2 = st.columns(2)

                with col1:

                    nombre_edit = st.text_input(
                        "Nombre",
                        value=str(proveedor_data["nombre"]),
                        key="editar_proveedor_nombre"
                    )

                    contacto_edit = st.text_input(
                        "Contacto",
                        value=limpiar_texto(proveedor_data["contacto"]).replace("-", ""),
                        key="editar_proveedor_contacto"
                    )

                    telefono_edit = st.text_input(
                        "Teléfono",
                        value=limpiar_texto(proveedor_data["telefono"]).replace("-", ""),
                        key="editar_proveedor_telefono"
                    )

                with col2:

                    correo_edit = st.text_input(
                        "Correo",
                        value=limpiar_texto(proveedor_data["correo"]).replace("-", ""),
                        key="editar_proveedor_correo"
                    )

                    dias_edit = st.number_input(
                        "Días de crédito",
                        min_value=0,
                        max_value=365,
                        value=int(
                            0 if pd.isna(proveedor_data["dias_credito"])
                            else proveedor_data["dias_credito"]
                        ),
                        key="editar_proveedor_dias"
                    )

                    estado_edit = st.selectbox(
                        "Estado",
                        estado_opciones,
                        index=index_estado,
                        key="editar_proveedor_estado"
                    )

                observaciones_edit = st.text_area(
                    "Observaciones",
                    value=observaciones_actuales,
                    height=90,
                    key="editar_proveedor_observaciones"
                )

                guardar_cambios_proveedor = st.form_submit_button(
                    "Guardar cambios del proveedor",
                    use_container_width=True
                )

            if guardar_cambios_proveedor:

                nombre_edit_limpio = nombre_edit.strip()

                if nombre_edit_limpio == "":

                    st.error("El nombre del proveedor es obligatorio.")

                else:

                    cursor.execute("""
                        SELECT COUNT(*)
                        FROM proveedores
                        WHERE UPPER(nombre) = UPPER(%s)
                        AND proveedor_id <> %s
                    """, (
                        nombre_edit_limpio,
                        proveedor_id
                    ))

                    existe_nombre = cursor.fetchone()[0]

                    if existe_nombre > 0:

                        st.warning("Ya existe otro proveedor con ese nombre.")

                    else:

                        try:

                            cursor.execute("""
                                UPDATE proveedores
                                SET
                                    nombre = %s,
                                    contacto = %s,
                                    telefono = %s,
                                    correo = %s,
                                    dias_credito = %s,
                                    estado = %s,
                                    observaciones = %s
                                WHERE proveedor_id = %s
                            """, (
                                nombre_edit_limpio,
                                contacto_edit.strip(),
                                telefono_edit.strip(),
                                correo_edit.strip(),
                                int(dias_edit),
                                estado_edit,
                                observaciones_edit.strip(),
                                proveedor_id
                            ))

                            conn.commit()

                            registrar_log(
                                st.session_state["usuario"],
                                "MODIFICACION_PROVEEDOR",
                                f"Modificó el proveedor {nombre_edit_limpio}"
                            )

                            st.success("Proveedor actualizado correctamente.")

                            st.rerun()

                        except Exception as e:

                            conn.rollback()

                            st.error(e)

            st.divider()

            st.markdown("#### Acciones rápidas")

            col1, col2 = st.columns(2)

            with col1:

                if st.button(
                    "Desactivar proveedor",
                    use_container_width=True,
                    disabled=estado_actual == "INACTIVO",
                    key="btn_desactivar_proveedor"
                ):

                    try:

                        cursor.execute("""
                            UPDATE proveedores
                            SET estado = 'INACTIVO'
                            WHERE proveedor_id = %s
                        """, (
                            proveedor_id,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "PROVEEDOR_DESACTIVADO",
                            f"Desactivó el proveedor ID {proveedor_id}"
                        )

                        st.success("Proveedor desactivado correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)

            with col2:

                if st.button(
                    "Reactivar proveedor",
                    use_container_width=True,
                    disabled=estado_actual == "ACTIVO",
                    key="btn_reactivar_proveedor"
                ):

                    try:

                        cursor.execute("""
                            UPDATE proveedores
                            SET estado = 'ACTIVO'
                            WHERE proveedor_id = %s
                        """, (
                            proveedor_id,
                        ))

                        conn.commit()

                        registrar_log(
                            st.session_state["usuario"],
                            "PROVEEDOR_REACTIVADO",
                            f"Reactivó el proveedor ID {proveedor_id}"
                        )

                        st.success("Proveedor reactivado correctamente.")

                        st.rerun()

                    except Exception as e:

                        conn.rollback()

                        st.error(e)
# ----------------------------
# AGREGAR FACTURA
# ----------------------------

with tab2:

    st.subheader("Agregar factura")

    df_proveedores_activos = pd.read_sql("""
        SELECT
            proveedor_id,
            nombre,
            contacto,
            telefono,
            correo,
            dias_credito
        FROM proveedores
        WHERE estado = 'ACTIVO'
        ORDER BY nombre ASC
    """, conn)

    if df_proveedores_activos.empty:

        st.warning("No existen proveedores activos para registrar facturas.")

    else:

        # ----------------------------
        # SELECCIÓN DE PROVEEDOR
        # ----------------------------

        proveedores_dict = {
            int(fila["proveedor_id"]): fila
            for _, fila in df_proveedores_activos.iterrows()
        }

        proveedor_id = st.selectbox(
            "Proveedor",
            options=list(proveedores_dict.keys()),
            format_func=lambda x: proveedores_dict[x]["nombre"],
            key="proveedor_nueva_factura"
        )

        proveedor_data = proveedores_dict[proveedor_id]

        proveedor_nombre = str(proveedor_data["nombre"])
        proveedor_contacto = "" if pd.isna(proveedor_data["contacto"]) else str(proveedor_data["contacto"])
        proveedor_telefono = "" if pd.isna(proveedor_data["telefono"]) else str(proveedor_data["telefono"])
        proveedor_correo = "" if pd.isna(proveedor_data["correo"]) else str(proveedor_data["correo"])

        dias_credito_default = (
            0 if pd.isna(proveedor_data["dias_credito"])
            else int(proveedor_data["dias_credito"])
        )

        # ----------------------------
        # TARJETA DEL PROVEEDOR
        # ----------------------------

        proveedor_html = f"""
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: transparent;
                font-family: Arial, sans-serif;
            }}

            .card-proveedor {{
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 18px 20px;
                background: #ffffff;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            }}

            .card-proveedor-contenido {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                flex-wrap: wrap;
            }}

            .label {{
                font-size: 13px;
                color: #64748b;
                font-weight: 600;
                margin-bottom: 5px;
            }}

            .proveedor-nombre {{
                font-size: 21px;
                color: #111827;
                font-weight: 800;
            }}

            .proveedor-info {{
                font-size: 13px;
                color: #475569;
                margin-top: 5px;
            }}

            .credito {{
                display: inline-block;
                background: #f1f5f9;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 999px;
                padding: 8px 14px;
                font-size: 13px;
                font-weight: 800;
            }}
        </style>

        <div class="card-proveedor">
            <div class="card-proveedor-contenido">
                <div>
                    <div class="label">Proveedor seleccionado</div>
                    <div class="proveedor-nombre">{escape(proveedor_nombre)}</div>
                    <div class="proveedor-info">
                        Contacto: {escape(proveedor_contacto or "-")} |
                        Tel: {escape(proveedor_telefono or "-")} |
                        Correo: {escape(proveedor_correo or "-")}
                    </div>
                </div>

                <div>
                    <span class="credito">{dias_credito_default} días de crédito</span>
                </div>
            </div>
        </div>
        """

        components.html(
            proveedor_html,
            height=125,
            scrolling=False
        )

        st.divider()

        # ----------------------------
        # CAPTURA DE FACTURA
        # ----------------------------

        st.markdown("### Datos de la factura")

        col1, col2 = st.columns(2)

        with col1:

            folio = st.text_input(
                "Folio de factura",
                key="folio_nueva_factura",
                placeholder="Ej. F12345"
            )

            fecha_factura = st.date_input(
                "Fecha de factura",
                value=date.today(),
                key="fecha_factura_nueva"
            )

            dias_credito = st.number_input(
                "Días de crédito",
                min_value=0,
                max_value=365,
                value=dias_credito_default,
                key=f"dias_credito_nueva_factura_{proveedor_id}"
            )

        with col2:

            monto = st.number_input(
                "Monto",
                min_value=0.0,
                step=100.0,
                format="%.2f",
                key="monto_nueva_factura"
            )

            estatus = st.selectbox(
                "Estatus inicial",
                ["PENDIENTE", "PAGADA"],
                key="estatus_nueva_factura"
            )

            modificar_vencimiento = st.checkbox(
                "Modificar vencimiento manualmente",
                value=False,
                key="modificar_vencimiento_nueva_factura"
            )

        fecha_vencimiento_calculada = (
            fecha_factura +
            timedelta(days=int(dias_credito))
        )

        if modificar_vencimiento:

            fecha_vencimiento = st.date_input(
                "Fecha de vencimiento",
                value=fecha_vencimiento_calculada,
                key="fecha_vencimiento_manual_nueva_factura"
            )

        else:

            fecha_vencimiento = fecha_vencimiento_calculada

            st.info(
                f"Fecha de vencimiento calculada automáticamente: {fecha_vencimiento.strftime('%d/%m/%Y')}"
            )

        observaciones = st.text_area(
            "Observaciones",
            height=90,
            key="observaciones_nueva_factura"
        )

        # ----------------------------
        # RESUMEN VISUAL ANTES DE GUARDAR
        # ----------------------------

        st.markdown("### Resumen antes de guardar")

        dias_restantes = (fecha_vencimiento - date.today()).days

        if estatus == "PAGADA":

            texto_estado = "PAGADA"
            detalle_estado = "Factura registrada como pagada"
            fondo_estado = "#e0f2fe"
            color_estado = "#075985"
            borde_estado = "#7dd3fc"

        elif dias_restantes < 0:

            texto_estado = "VENCIDA"
            detalle_estado = f"Venció hace {abs(dias_restantes)} días"
            fondo_estado = "#fee2e2"
            color_estado = "#991b1b"
            borde_estado = "#fca5a5"

        elif dias_restantes == 0:

            texto_estado = "VENCE HOY"
            detalle_estado = "Debe pagarse hoy"
            fondo_estado = "#ffedd5"
            color_estado = "#9a3412"
            borde_estado = "#fdba74"

        elif dias_restantes <= 7:

            texto_estado = "POR VENCER"
            detalle_estado = f"Faltan {dias_restantes} días"
            fondo_estado = "#ffedd5"
            color_estado = "#9a3412"
            borde_estado = "#fdba74"

        else:

            texto_estado = "EN TIEMPO"
            detalle_estado = f"Faltan {dias_restantes} días"
            fondo_estado = "#dcfce7"
            color_estado = "#166534"
            borde_estado = "#86efac"

        folio_resumen = folio.strip() if folio.strip() else "Sin capturar"

        resumen_html = f"""
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: transparent;
                font-family: Arial, sans-serif;
            }}

            .card-resumen {{
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 20px 22px;
                background: #ffffff;
                box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
            }}

            .resumen-contenido {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                flex-wrap: wrap;
            }}

            .label {{
                font-size: 13px;
                color: #64748b;
                font-weight: 600;
                margin-bottom: 5px;
            }}

            .titulo {{
                font-size: 21px;
                color: #111827;
                font-weight: 800;
            }}

            .detalle {{
                font-size: 14px;
                color: #475569;
                margin-top: 5px;
                line-height: 1.6;
            }}

            .lado-derecho {{
                text-align: right;
            }}

            .badge-estado {{
                display: inline-block;
                background: {fondo_estado};
                color: {color_estado};
                border: 1px solid {borde_estado};
                border-radius: 999px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.3px;
            }}

            .monto {{
                font-size: 25px;
                color: #111827;
                font-weight: 800;
                margin-top: 10px;
            }}

            .detalle-estado {{
                font-size: 13px;
                color: #64748b;
                margin-top: 6px;
            }}
        </style>

        <div class="card-resumen">
            <div class="resumen-contenido">
                <div>
                    <div class="label">Factura por registrar</div>
                    <div class="titulo">{escape(proveedor_nombre)}</div>
                    <div class="detalle">
                        Folio: <strong>{escape(folio_resumen)}</strong><br>
                        Fecha factura: <strong>{fecha_factura.strftime('%d/%m/%Y')}</strong><br>
                        Vencimiento: <strong>{fecha_vencimiento.strftime('%d/%m/%Y')}</strong><br>
                        Crédito: <strong>{int(dias_credito)} días</strong>
                    </div>
                </div>

                <div class="lado-derecho">
                    <span class="badge-estado">{texto_estado}</span>
                    <div class="detalle-estado">{detalle_estado}</div>
                    <div class="monto">${float(monto):,.2f}</div>
                </div>
            </div>
        </div>
        """

        components.html(
            resumen_html,
            height=210,
            scrolling=False
        )

        st.divider()

        # ----------------------------
        # GUARDAR FACTURA
        # ----------------------------

        if st.button(
            "Guardar factura",
            type="primary",
            use_container_width=True,
            key="btn_guardar_nueva_factura"
        ):

            if folio.strip() == "":

                st.error("El folio de la factura es obligatorio.")
                st.stop()

            if monto <= 0:

                st.error("El monto debe ser mayor a 0.")
                st.stop()

            cursor.execute("""
                SELECT COUNT(*)
                FROM facturas
                WHERE proveedor_id = %s
                AND UPPER(folio) = UPPER(%s)
            """, (
                int(proveedor_id),
                folio.strip()
            ))

            existe_factura = cursor.fetchone()[0]

            if existe_factura > 0:

                st.error("Ya existe una factura con ese folio para este proveedor.")
                st.stop()

            try:

                cursor.execute("""
                    INSERT INTO facturas
                    (
                        proveedor_id,
                        folio,
                        fecha_factura,
                        dias_credito,
                        fecha_vencimiento,
                        monto,
                        estatus,
                        observaciones
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    int(proveedor_id),
                    folio.strip(),
                    fecha_factura,
                    int(dias_credito),
                    fecha_vencimiento,
                    float(monto),
                    estatus,
                    observaciones.strip()
                ))

                conn.commit()

                registrar_log(
                    st.session_state["usuario"],
                    "ALTA_FACTURA",
                    f"Registró la factura {folio.strip()} del proveedor {proveedor_nombre}"
                )

                st.success("Factura registrada correctamente.")

                st.session_state.pop("folio_nueva_factura", None)
                st.session_state.pop("monto_nueva_factura", None)
                st.session_state.pop("observaciones_nueva_factura", None)

                st.rerun()

            except Exception as e:

                conn.rollback()

                st.error(e)
                st.divider()

        # ----------------------------
        # ÚLTIMAS FACTURAS REGISTRADAS
        # ----------------------------

        st.markdown("### Últimas facturas registradas")

        df_ultimas_facturas = pd.read_sql("""
            SELECT
                f.factura_id,
                p.nombre AS proveedor,
                f.folio,
                f.fecha_factura,
                f.fecha_vencimiento,
                f.monto,
                f.estatus
            FROM facturas f
            LEFT JOIN proveedores p
                ON f.proveedor_id = p.proveedor_id
            ORDER BY f.created_at DESC
            LIMIT 8
        """, conn)

        if df_ultimas_facturas.empty:

            st.info("Todavía no hay facturas registradas.")

        else:

            df_ultimas_facturas["fecha_factura"] = pd.to_datetime(
                df_ultimas_facturas["fecha_factura"]
            ).dt.strftime("%d/%m/%Y")

            df_ultimas_facturas["fecha_vencimiento"] = pd.to_datetime(
                df_ultimas_facturas["fecha_vencimiento"]
            ).dt.strftime("%d/%m/%Y")

            df_ultimas_facturas["monto"] = df_ultimas_facturas["monto"].astype(float)

            estilos_ultimas = """
            <style>
                body {
                    margin: 0;
                    padding: 0;
                    background: transparent;
                    font-family: Arial, sans-serif;
                }

                .ultimas-contenedor {
                    width: 100%;
                    overflow-x: auto;
                    border-radius: 16px;
                    border: 1px solid #e5e7eb;
                    background: #ffffff;
                    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
                }

                .tabla-ultimas {
                    width: 100%;
                    border-collapse: separate;
                    border-spacing: 0;
                    font-size: 14px;
                }

                .tabla-ultimas thead th {
                    background: #f8fafc;
                    color: #334155;
                    text-align: left;
                    padding: 14px 16px;
                    font-weight: 700;
                    border-bottom: 1px solid #e5e7eb;
                    white-space: nowrap;
                }

                .tabla-ultimas tbody td {
                    padding: 14px 16px;
                    border-bottom: 1px solid #f1f5f9;
                    color: #1f2937;
                    vertical-align: middle;
                    background: #ffffff;
                }

                .tabla-ultimas tbody tr:hover td {
                    background: #f8fafc;
                }

                .proveedor-ultima {
                    font-weight: 800;
                    color: #111827;
                }

                .folio-ultima {
                    font-weight: 700;
                    color: #334155;
                    background: #f1f5f9;
                    padding: 5px 9px;
                    border-radius: 8px;
                    display: inline-block;
                }

                .monto-ultima {
                    font-weight: 800;
                    color: #111827;
                    white-space: nowrap;
                    text-align: right;
                }

                .badge-pendiente {
                    background: #ffedd5;
                    color: #9a3412;
                    border: 1px solid #fdba74;
                    border-radius: 999px;
                    padding: 6px 10px;
                    font-size: 12px;
                    font-weight: 800;
                    display: inline-block;
                }

                .badge-pagada {
                    background: #e0f2fe;
                    color: #075985;
                    border: 1px solid #7dd3fc;
                    border-radius: 999px;
                    padding: 6px 10px;
                    font-size: 12px;
                    font-weight: 800;
                    display: inline-block;
                }

                .badge-cancelada {
                    background: #ffffff;
                    color: #64748b;
                    border: 1px solid #cbd5e1;
                    border-radius: 999px;
                    padding: 6px 10px;
                    font-size: 12px;
                    font-weight: 800;
                    display: inline-block;
                }
            </style>
            """

            filas_ultimas = ""

            for _, fila in df_ultimas_facturas.iterrows():

                estatus = str(fila["estatus"]).upper()

                if estatus == "PAGADA":

                    badge = '<span class="badge-pagada">PAGADA</span>'

                elif estatus == "CANCELADA":

                    badge = '<span class="badge-cancelada">CANCELADA</span>'

                else:

                    badge = '<span class="badge-pendiente">PENDIENTE</span>'

                filas_ultimas += f"""
                    <tr>
                        <td><span class="proveedor-ultima">{escape(str(fila["proveedor"] or "-"))}</span></td>
                        <td><span class="folio-ultima">{escape(str(fila["folio"] or "-"))}</span></td>
                        <td>{fila["fecha_factura"]}</td>
                        <td>{fila["fecha_vencimiento"]}</td>
                        <td>{badge}</td>
                        <td class="monto-ultima">${float(fila["monto"]):,.2f}</td>
                    </tr>
                """

            ultimas_html = f"""
            {estilos_ultimas}

            <div class="ultimas-contenedor">
                <table class="tabla-ultimas">
                    <thead>
                        <tr>
                            <th>Proveedor</th>
                            <th>Folio</th>
                            <th>Fecha factura</th>
                            <th>Vencimiento</th>
                            <th>Estatus</th>
                            <th>Monto</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filas_ultimas}
                    </tbody>
                </table>
            </div>
            """

            altura_ultimas = min(
                620,
                130 + (len(df_ultimas_facturas) * 68)
            )

            components.html(
                ultimas_html,
                height=altura_ultimas,
                scrolling=True
            )

# ----------------------------
# ESTADÍSTICAS DE FACTURAS
# ----------------------------

with tab4:

    st.subheader("Estadísticas de facturas")

    df_estadisticas = pd.read_sql("""
        SELECT
            f.factura_id,
            p.nombre AS proveedor,
            f.folio,
            f.fecha_factura,
            f.fecha_vencimiento,
            f.dias_credito,
            f.monto,
            f.estatus,
            f.observaciones
        FROM facturas f
        LEFT JOIN proveedores p
            ON f.proveedor_id = p.proveedor_id
        ORDER BY f.fecha_factura DESC
    """, conn)

    if df_estadisticas.empty:

        st.info("Todavía no hay facturas registradas para generar estadísticas.")

    else:

        df_estadisticas["fecha_factura"] = pd.to_datetime(
            df_estadisticas["fecha_factura"]
        )

        df_estadisticas["fecha_vencimiento"] = pd.to_datetime(
            df_estadisticas["fecha_vencimiento"]
        )

        hoy = pd.Timestamp(date.today())

        df_estadisticas["dias_restantes"] = (
            df_estadisticas["fecha_vencimiento"] - hoy
        ).dt.days

        df_estadisticas["mes"] = (
            df_estadisticas["fecha_factura"]
            .dt.to_period("M")
            .astype(str)
        )

        df_estadisticas["monto"] = df_estadisticas["monto"].astype(float)

        # ----------------------------
        # FILTROS
        # ----------------------------

        st.markdown("### Filtros")

        col1, col2, col3 = st.columns(3)

        with col1:

            proveedores = ["Todos"] + sorted(
                df_estadisticas["proveedor"].dropna().unique().tolist()
            )

            filtro_proveedor_est = st.selectbox(
                "Proveedor",
                proveedores,
                key="filtro_proveedor_estadisticas"
            )

        with col2:

            estatus_est = st.selectbox(
                "Estatus",
                [
                    "Todos",
                    "PENDIENTE",
                    "PAGADA",
                    "CANCELADA"
                ],
                key="filtro_estatus_estadisticas"
            )

        with col3:

            meses = ["Todos"] + sorted(
                df_estadisticas["mes"].dropna().unique().tolist(),
                reverse=True
            )

            filtro_mes_est = st.selectbox(
                "Mes",
                meses,
                key="filtro_mes_estadisticas"
            )

        df_stats = df_estadisticas.copy()

        if filtro_proveedor_est != "Todos":

            df_stats = df_stats[
                df_stats["proveedor"] == filtro_proveedor_est
            ]

        if estatus_est != "Todos":

            df_stats = df_stats[
                df_stats["estatus"] == estatus_est
            ]

        if filtro_mes_est != "Todos":

            df_stats = df_stats[
                df_stats["mes"] == filtro_mes_est
            ]

        if df_stats.empty:

            st.warning("No hay información con los filtros seleccionados.")

        else:

            # ----------------------------
            # KPIS PRINCIPALES
            # ----------------------------

            pendientes = df_stats[
                df_stats["estatus"] == "PENDIENTE"
            ]

            pagadas = df_stats[
                df_stats["estatus"] == "PAGADA"
            ]

            canceladas = df_stats[
                df_stats["estatus"] == "CANCELADA"
            ]

            vencidas = df_stats[
                (df_stats["estatus"] == "PENDIENTE") &
                (df_stats["dias_restantes"] < 0)
            ]

            proximas = df_stats[
                (df_stats["estatus"] == "PENDIENTE") &
                (df_stats["dias_restantes"] >= 0) &
                (df_stats["dias_restantes"] <= 7)
            ]

            col1, col2, col3, col4 = st.columns(4)

            with col1:

                st.metric(
                    "Saldo pendiente",
                    f"${pendientes['monto'].sum():,.2f}"
                )

            with col2:

                st.metric(
                    "Facturas pendientes",
                    len(pendientes)
                )

            with col3:

                st.metric(
                    "Facturas vencidas",
                    len(vencidas)
                )

            with col4:

                st.metric(
                    "Vencen en 7 días",
                    len(proximas)
                )

            col1, col2, col3, col4 = st.columns(4)

            with col1:

                st.metric(
                    "Monto vencido",
                    f"${vencidas['monto'].sum():,.2f}"
                )

            with col2:

                st.metric(
                    "Monto pagado",
                    f"${pagadas['monto'].sum():,.2f}"
                )

            with col3:

                st.metric(
                    "Facturas canceladas",
                    len(canceladas)
                )

            with col4:

                st.metric(
                    "Total registrado",
                    f"${df_stats['monto'].sum():,.2f}"
                )

            st.divider()

            # ----------------------------
            # GRÁFICAS
            # ----------------------------

            col1, col2 = st.columns(2)

            with col1:

                st.markdown("### Monto por estatus")

                df_estatus = (
                    df_stats
                    .groupby("estatus", as_index=False)["monto"]
                    .sum()
                    .sort_values("monto", ascending=False)
                )

                fig_estatus = px.bar(
                    df_estatus,
                    x="estatus",
                    y="monto",
                    text_auto=".2s",
                    title="Monto total por estatus"
                )

                fig_estatus.update_layout(
                    xaxis_title="Estatus",
                    yaxis_title="Monto",
                    showlegend=False
                )

                st.plotly_chart(
                    fig_estatus,
                    use_container_width=True
                )

            with col2:

                st.markdown("### Número de facturas por estatus")

                df_conteo_estatus = (
                    df_stats
                    .groupby("estatus", as_index=False)["factura_id"]
                    .count()
                    .rename(columns={"factura_id": "cantidad"})
                    .sort_values("cantidad", ascending=False)
                )

                fig_conteo = px.pie(
                    df_conteo_estatus,
                    names="estatus",
                    values="cantidad",
                    title="Distribución de facturas"
                )

                st.plotly_chart(
                    fig_conteo,
                    use_container_width=True
                )

            st.divider()

            col1, col2 = st.columns(2)

            with col1:

                st.markdown("### Proveedores con mayor saldo pendiente")

                df_pendiente_proveedor = (
                    pendientes
                    .groupby("proveedor", as_index=False)["monto"]
                    .sum()
                    .sort_values("monto", ascending=False)
                    .head(10)
                )

                if df_pendiente_proveedor.empty:

                    st.info("No hay saldo pendiente para graficar.")

                else:

                    fig_pendiente = px.bar(
                        df_pendiente_proveedor,
                        x="monto",
                        y="proveedor",
                        orientation="h",
                        text_auto=".2s",
                        title="Top proveedores por saldo pendiente"
                    )

                    fig_pendiente.update_layout(
                        xaxis_title="Monto pendiente",
                        yaxis_title="Proveedor",
                        yaxis=dict(autorange="reversed")
                    )

                    st.plotly_chart(
                        fig_pendiente,
                        use_container_width=True
                    )

            with col2:

                st.markdown("### Compras por proveedor")

                df_compras_proveedor = (
                    df_stats[df_stats["estatus"] != "CANCELADA"]
                    .groupby("proveedor", as_index=False)["monto"]
                    .sum()
                    .sort_values("monto", ascending=False)
                    .head(10)
                )

                if df_compras_proveedor.empty:

                    st.info("No hay compras para graficar.")

                else:

                    fig_compras = px.bar(
                        df_compras_proveedor,
                        x="monto",
                        y="proveedor",
                        orientation="h",
                        text_auto=".2s",
                        title="Top proveedores por monto facturado"
                    )

                    fig_compras.update_layout(
                        xaxis_title="Monto facturado",
                        yaxis_title="Proveedor",
                        yaxis=dict(autorange="reversed")
                    )

                    st.plotly_chart(
                        fig_compras,
                        use_container_width=True
                    )

            st.divider()

            # ----------------------------
            # TENDENCIA MENSUAL
            # ----------------------------

            st.markdown("### Monto facturado por mes")

            df_mensual = (
                df_stats[df_stats["estatus"] != "CANCELADA"]
                .groupby("mes", as_index=False)["monto"]
                .sum()
                .sort_values("mes")
            )

            if df_mensual.empty:

                st.info("No hay información mensual para graficar.")

            else:

                fig_mensual = px.line(
                    df_mensual,
                    x="mes",
                    y="monto",
                    markers=True,
                    title="Evolución mensual del monto facturado"
                )

                fig_mensual.update_layout(
                    xaxis_title="Mes",
                    yaxis_title="Monto facturado"
                )

                st.plotly_chart(
                    fig_mensual,
                    use_container_width=True
                )

            st.divider()

            # ----------------------------
            # TABLA DE PRÓXIMOS VENCIMIENTOS
            # ----------------------------

            st.markdown("### Próximos vencimientos")

            df_proximos = (
                df_stats[
                    (df_stats["estatus"] == "PENDIENTE") &
                    (df_stats["dias_restantes"] >= 0)
                ]
                .sort_values("dias_restantes")
                .head(10)
            )

            if df_proximos.empty:

                st.info("No hay facturas próximas a vencer.")

            else:

                df_proximos_mostrar = df_proximos[[
                    "proveedor",
                    "folio",
                    "fecha_vencimiento",
                    "dias_restantes",
                    "monto"
                ]].copy()

                df_proximos_mostrar["fecha_vencimiento"] = (
                    df_proximos_mostrar["fecha_vencimiento"]
                    .dt.strftime("%d/%m/%Y")
                )

                df_proximos_mostrar = df_proximos_mostrar.rename(columns={
                    "proveedor": "Proveedor",
                    "folio": "Folio",
                    "fecha_vencimiento": "Fecha vencimiento",
                    "dias_restantes": "Días restantes",
                    "monto": "Monto"
                })

                st.dataframe(
                    df_proximos_mostrar,
                    use_container_width=True,
                    hide_index=True
                )
# ===============================
# SIDEBAR INFO
# ===============================
st.sidebar.success(
    f"👤 {st.session_state['usuario']['nombre']}\n"
    f"Rol: {st.session_state['usuario']['rol']}"
)

if st.sidebar.button("🚪 Cerrar sesión"):
    st.session_state.clear()
    st.switch_page("streamlit_app.py")
