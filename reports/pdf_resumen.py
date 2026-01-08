from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
from io import BytesIO


def generar_pdf_resumen_financiero(
    df_ventas,
    df_gastos,
    periodo,
    farmacia
):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    elementos = []

    # ===============================
    # ESTILOS
    # ===============================
    titulo = ParagraphStyle(
        "titulo",
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor("#1F2937")
    )

    subtitulo = ParagraphStyle(
        "subtitulo",
        fontSize=11,
        alignment=TA_CENTER,
        textColor=colors.grey
    )

    seccion = ParagraphStyle(
        "seccion",
        fontSize=13,
        spaceBefore=14,
        spaceAfter=8,
        textColor=colors.HexColor("#111827")
    )

    normal = ParagraphStyle(
        "normal",
        fontSize=10,
        textColor=colors.black
    )

    # ===============================
    # ENCABEZADO
    # ===============================
    elementos.append(Paragraph("Farmacias GI", titulo))
    elementos.append(Paragraph("Resumen Financiero", subtitulo))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(
        f"<b>Periodo:</b> {periodo}", normal
    ))
    elementos.append(Paragraph(
        f"<b>Farmacia:</b> {farmacia}", normal
    ))

    elementos.append(Spacer(1, 16))

    # ===============================
    # KPIs PRINCIPALES
    # ===============================
    ventas_total = df_ventas["ventas_totales"].sum()
    gastos_total = df_gastos["monto"].sum()
    utilidad = ventas_total - gastos_total
    margen = (utilidad / ventas_total * 100) if ventas_total > 0 else 0

    tabla_kpi = Table(
        [
            ["Ventas Totales", "Gastos Totales", "Utilidad Neta", "Margen"],
            [
                f"${ventas_total:,.2f}",
                f"${gastos_total:,.2f}",
                f"${utilidad:,.2f}",
                f"{margen:.2f}%"
            ]
        ],
        colWidths=[4 * cm] * 4
    )

    tabla_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
    ]))

    elementos.append(tabla_kpi)

    # ===============================
    # RESUMEN DE GASTOS
    # ===============================
    elementos.append(Paragraph("Resumen de Gastos", seccion))

    gastos_fijos = df_gastos[df_gastos["tipo_gasto"] == "fijo"]["monto"].sum()
    gastos_variables = df_gastos[df_gastos["tipo_gasto"] == "variable"]["monto"].sum()

    elementos.append(Paragraph(
        f"Gastos fijos: <b>${gastos_fijos:,.2f}</b>", normal
    ))
    elementos.append(Paragraph(
        f"Gastos variables: <b>${gastos_variables:,.2f}</b>", normal
    ))

    # Top 3 categorías
    top_categorias = (
        df_gastos.groupby("categoria")["monto"]
        .sum()
        .sort_values(ascending=False)
        .head(3)
    )

    if not top_categorias.empty:
        elementos.append(Spacer(1, 8))
        elementos.append(Paragraph("Principales categorías:", normal))

        for cat, monto in top_categorias.items():
            elementos.append(Paragraph(
                f"- {cat}: ${monto:,.2f}", normal
            ))

    # ===============================
    # FOOTER
    # ===============================
    elementos.append(Spacer(1, 20))
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    elementos.append(Paragraph(
        f"Reporte generado el {fecha}", 
        ParagraphStyle(
            "footer",
            fontSize=8,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
    ))

    # ===============================
    # GENERAR
    # ===============================
    doc.build(elementos)
    buffer.seek(0)
    return buffer
