from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm
from datetime import datetime
import io
import pandas as pd


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
    elementos = []

    # -----------------------------
    # PORTADA
    # -----------------------------
    elementos.append(Spacer(1, 3 * cm))
    elementos.append(Paragraph("<b>Farmacias GI</b>", styles["Title"]))
    elementos.append(Spacer(1, 12))
    elementos.append(Paragraph("Reporte de Gastos", styles["Title"]))
    elementos.append(Spacer(1, 24))

    elementos.append(Paragraph(f"<b>Periodo:</b> {periodo}", styles["Normal"]))
    elementos.append(Paragraph(f"<b>Farmacia:</b> {farmacia}", styles["Normal"]))
    elementos.append(
        Paragraph(
            f"<b>Fecha de generación:</b> {datetime.now().strftime('%d/%m/%Y')}",
            styles["Normal"]
        )
    )

    elementos.append(Spacer(1, 2 * cm))

    # Salto de página
    elementos.append(Spacer(1, 500))

    # -----------------------------
    # RESUMEN EJECUTIVO
    # -----------------------------
    elementos.append(Paragraph("Resumen Ejecutivo", styles["Heading1"]))
    elementos.append(Spacer(1, 12))

    total_gastos = df_gastos["monto"].sum()
    total_registros = len(df_gastos)

    if not df_gastos.empty:
        categoria_top = (
            df_gastos.groupby("categoria")["monto"]
            .sum()
            .idxmax()
        )
    else:
        categoria_top = "N/A"

    resumen_texto = f"""
    Durante el periodo analizado se registraron <b>{total_registros}</b> gastos,
    con un monto total de <b>${total_gastos:,.2f}</b>.
    La categoría con mayor impacto fue <b>{categoria_top}</b>.
    """

    elementos.append(Paragraph(resumen_texto, styles["Normal"]))
    elementos.append(Spacer(1, 24))

    # -----------------------------
    # TABLA DE GASTOS
    # -----------------------------
    elementos.append(Paragraph("Detalle de Gastos", styles["Heading1"]))
    elementos.append(Spacer(1, 12))

    tabla_data = [
        [
            "Fecha",
            "Farmacia",
            "Categoría",
            "Tipo",
            "Descripción",
            "Monto"
        ]
    ]

    df_tabla = df_gastos.sort_values("fecha")

    for _, row in df_tabla.iterrows():
        tabla_data.append([
            row["fecha"].strftime("%d/%m/%Y"),
            row["farmacia"],
            row["categoria"],
            row["tipo_gasto"],
            row["descripcion"],
            f"${row['monto']:,.2f}"
        ])

    tabla = Table(tabla_data, repeatRows=1, colWidths=[
        2.2 * cm,
        3 * cm,
        3 * cm,
        2.5 * cm,
        4 * cm,
        2.3 * cm
    ])

    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEEEE")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))

    elementos.append(tabla)

    # -----------------------------
    # CONCLUSIÓN
    # -----------------------------
    elementos.append(Spacer(1, 24))
    elementos.append(Paragraph("Conclusión", styles["Heading2"]))

    conclusion = """
    Se recomienda revisar periódicamente los gastos con mayor recurrencia
    y validar que cuenten con una descripción clara para mantener
    un control financiero adecuado.
    """

    elementos.append(Paragraph(conclusion, styles["Normal"]))

    # -----------------------------
    # GENERAR PDF
    # -----------------------------
    doc.build(elementos)
    buffer.seek(0)

    return buffer.getvalue()
