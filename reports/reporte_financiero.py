from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime


def generar_reporte_financiero(df_ventas, df_gastos, periodo):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    story = []

    # ===============================
    # PORTADA
    # ===============================
    titulo = Paragraph(
        "<b>REPORTE FINANCIERO</b>",
        styles["Title"]
    )
    subtitulo = Paragraph(
        f"<b>Periodo:</b> {periodo}",
        styles["Heading2"]
    )
    fecha = Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y')}",
        styles["Normal"]
    )

    story.extend([titulo, Spacer(1, 20), subtitulo, Spacer(1, 10), fecha])
    story.append(Spacer(1, 40))

    # ===============================
    # RESUMEN EJECUTIVO
    # ===============================
    ventas_total = df_ventas["ventas_totales"].sum()
    gastos_total = df_gastos["monto"].sum()
    utilidad = ventas_total - gastos_total
    margen = (utilidad / ventas_total * 100) if ventas_total > 0 else 0

    story.append(Paragraph("<b>Resumen Ejecutivo</b>", styles["Heading2"]))
    story.append(Spacer(1, 10))

    resumen = f"""
    Ventas totales: ${ventas_total:,.2f}<br/>
    Gastos totales: ${gastos_total:,.2f}<br/>
    Utilidad operativa: ${utilidad:,.2f}<br/>
    Margen: {margen:.2f}%
    """
    story.append(Paragraph(resumen, styles["Normal"]))
    story.append(Spacer(1, 25))

    # ===============================
    # ESTADO DE RESULTADOS
    # ===============================
    story.append(Paragraph("<b>Estado de Resultados</b>", styles["Heading2"]))
    story.append(Spacer(1, 10))

    tabla_er = [
        ["Concepto", "Monto"],
        ["Ventas", f"${ventas_total:,.2f}"],
        ["Gastos", f"${gastos_total:,.2f}"],
        ["Utilidad", f"${utilidad:,.2f}"],
    ]

    tabla = Table(tabla_er, colWidths=[250, 200])
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    story.append(tabla)
    story.append(Spacer(1, 30))

    # ===============================
    # UTILIDAD POR FARMACIA
    # ===============================
    story.append(Paragraph("<b>Utilidad por Farmacia</b>", styles["Heading2"]))
    story.append(Spacer(1, 10))

    util_farma = (
        df_ventas.groupby("farmacia")["ventas_totales"].sum()
        .reset_index()
        .merge(
            df_gastos.groupby("farmacia")["monto"].sum().reset_index(),
            on="farmacia",
            how="left"
        )
    )

    util_farma["monto"] = util_farma["monto"].fillna(0)
    util_farma["utilidad"] = util_farma["ventas_totales"] - util_farma["monto"]

    data = [["Farmacia", "Ventas", "Gastos", "Utilidad"]]

    for _, r in util_farma.iterrows():
        data.append([
            r["farmacia"],
            f"${r['ventas_totales']:,.2f}",
            f"${r['monto']:,.2f}",
            f"${r['utilidad']:,.2f}",
        ])

    tabla_util = Table(data, colWidths=[150, 120, 120, 120])
    tabla_util.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
    ]))

    story.append(tabla_util)

    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()
