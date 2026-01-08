from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
import pandas as pd
import io


def generar_pdf_gastos(df_gastos, periodo, farmacia):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm
    )

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="Titulo",
        fontSize=20,
        alignment=TA_CENTER,
        spaceAfter=20
    ))

    styles.add(ParagraphStyle(
        name="Subtitulo",
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.grey
    ))

    styles.add(ParagraphStyle(
        name="Encabezado",
        fontSize=11,
        spaceAfter=6,
        leading=14,
        fontName="Helvetica-Bold"
    ))

    styles.add(ParagraphStyle(
        name="Derecha",
        alignment=TA_RIGHT
    ))

    styles.add(ParagraphStyle(
        name="Descripcion",
        fontSize=9,
        leading=12
    ))

    elementos = []

    # ===============================
    # PORTADA
    # ===============================
    elementos.append(Paragraph("Farmacias GI", styles["Titulo"]))
    elementos.append(Paragraph("Reporte de Gastos", styles["Subtitulo"]))
    elementos.append(Spacer(1, 12))

    elementos.append(Paragraph(f"<b>Periodo:</b> {periodo}", styles["Normal"]))
    elementos.append(Paragraph(
        f"<b>Farmacia:</b> {farmacia if farmacia != 'Todas' else 'Todas'}",
        styles["Normal"]
    ))
    elementos.append(Paragraph(
        f"<b>Fecha de generación:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        styles["Normal"]
    ))

    elementos.append(Spacer(1, 24))

    # ===============================
    # RESUMEN EJECUTIVO
    # ===============================
    total_gastos = df_gastos["monto"].sum()
    total_registros = len(df_gastos)

    resumen_data = [
        ["Indicador", "Valor"],
        ["Total de gastos", f"${total_gastos:,.2f}"],
        ["Número de registros", total_registros],
    ]

    resumen_table = Table(resumen_data, colWidths=[7 * cm, 6 * cm])
    resumen_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))

    elementos.append(Paragraph("Resumen Ejecutivo", styles["Encabezado"]))
    elementos.append(resumen_table)
    elementos.append(Spacer(1, 24))

    # ===============================
    # TABLA DE GASTOS
    # ===============================
    elementos.append(Paragraph("Detalle de Gastos", styles["Encabezado"]))
    elementos.append(Spacer(1, 6))

    data = [
        ["Fecha", "Farmacia", "Categoría", "Descripción", "Monto"]
    ]

    for _, row in df_gastos.iterrows():
        data.append([
            row["fecha"].strftime("%d/%m/%Y"),
            row["farmacia"],
            row["categoria"] or "-",
            Paragraph(row["descripcion"] or "-", styles["Descripcion"]),
            Paragraph(f"${row['monto']:,.2f}", styles["Derecha"])
        ])

    tabla = Table(
        data,
        colWidths=[2.5 * cm, 4 * cm, 3 * cm, 6 * cm, 3 * cm],
        repeatRows=1
    )

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E6E6E6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
    ]))

    elementos.append(tabla)

    # ===============================
    # GENERAR PDF
    # ===============================
    doc.build(elementos)
    buffer.seek(0)
    return buffer
