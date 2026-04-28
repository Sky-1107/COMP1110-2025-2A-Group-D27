import csv
import io
from typing import List
from flask import Response
from budget_core import Transaction


def export_csv(transactions: List[Transaction]) -> Response:
    """
    Export transactions to CSV and return as Flask Response.
    """

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Date', 'Amount', 'Category', 'Description', 'Notes'])
    for tx in transactions:
        writer.writerow([tx.id, tx.date.strftime('%Y-%m-%d'), f"{tx.amount:.2f}", tx.category, tx.description, tx.notes])
    
    output.seek(0)
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.csv'
    return response


def export_pdf(transactions: List[Transaction]) -> Response:
    """
    Export transactions to PDF using reportlab.
    """
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        # Fallback if reportlab not installed
        return Response("PDF export requires reportlab. Install with: pip install reportlab", status=500)
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Transaction Report", styles['Title']))
    
    data = [['ID', 'Date', 'Amount', 'Category', 'Description', 'Notes']]
    for tx in transactions:
        data.append([
            str(tx.id),
            tx.date.strftime('%Y-%m-%d'),
            f"{tx.amount:.2f}",
            tx.category,
            tx.description,
            tx.notes
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    response = Response(buffer.getvalue(), mimetype='application/pdf')
    response.headers['Content-Disposition'] = 'attachment; filename=transactions.pdf'
    return response