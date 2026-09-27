"""
Executive Summary PDF Generator for Northwind Monday Screen

Creates a one-page board-ready report with:
- Critical alerts
- Weekly activity summary
- Top 10 shareholders
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
import pandas as pd
from datetime import datetime


def generate_executive_pdf(watch_list_df, weekly_activity_df, top_holders_df, alert_summary):
    """
    Generate executive summary PDF.

    Args:
        watch_list_df: DataFrame with watch list alerts
        weekly_activity_df: DataFrame with weekly activity by holder type
        top_holders_df: DataFrame with top 10 shareholders
        alert_summary: dict with alert counts

    Returns:
        bytes: PDF file content
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           topMargin=0.5*inch, bottomMargin=0.5*inch,
                           leftMargin=0.5*inch, rightMargin=0.5*inch)

    # Container for the 'Flowable' objects
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1976D2'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#333333'),
        spaceAfter=8,
        spaceBefore=12
    )
    normal_style = styles['Normal']

    # ==================
    # TITLE
    # ==================
    title = Paragraph("<b>Northwind Metals Corp</b><br/>Weekly Ownership Intelligence Report", title_style)
    elements.append(title)

    subtitle = Paragraph(
        f"Week ending August 31, 2026 | Generated: {datetime.now().strftime('%B %d, %Y')}",
        normal_style
    )
    elements.append(subtitle)
    elements.append(Spacer(1, 0.2*inch))

    # ==================
    # CRITICAL ALERTS
    # ==================
    alert_heading = Paragraph("<b>🚨 Critical Governance Alerts</b>", heading_style)
    elements.append(alert_heading)

    # Alert summary counts
    alert_data = [
        ['Alert Type', 'Count', 'Priority'],
        ['Activist Intent (13G→13D)', str(alert_summary['activist_alerts']), 'CRITICAL'],
        ['10% Threshold Crossings', str(alert_summary['threshold_10_alerts']), 'HIGH'],
        ['5% Threshold Crossings', str(alert_summary['threshold_5_alerts']), 'MEDIUM']
    ]

    alert_table = Table(alert_data, colWidths=[3.5*inch, 0.8*inch, 1*inch])
    alert_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    elements.append(alert_table)

    # Top 3 alerts detail
    if len(watch_list_df) > 0:
        elements.append(Spacer(1, 0.1*inch))
        alert_detail_para = Paragraph("<b>Top Alert Details:</b>", normal_style)
        elements.append(alert_detail_para)

        top_alerts = watch_list_df.head(3)[['filer_name', 'alert_type', 'date_happened']].values.tolist()
        alert_detail_data = [['Filer', 'Alert Type', 'Event Date']] + top_alerts

        alert_detail_table = Table(alert_detail_data, colWidths=[2.2*inch, 2.5*inch, 1*inch])
        alert_detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(alert_detail_table)

    elements.append(Spacer(1, 0.2*inch))

    # ==================
    # WEEKLY ACTIVITY
    # ==================
    activity_heading = Paragraph("<b>📈 Weekly Activity Pulse (Aug 24-28)</b>", heading_style)
    elements.append(activity_heading)

    if len(weekly_activity_df) > 0:
        # Format numbers
        activity_data = [['Holder Type', 'Bought', 'Sold', 'Net Change']]
        for _, row in weekly_activity_df.iterrows():
            activity_data.append([
                row['holder_type'],
                f"{int(row['shares_bought']):,}",
                f"{int(row['shares_sold']):,}",
                f"{int(row['net_change']):+,}"
            ])

        activity_table = Table(activity_data, colWidths=[1.5*inch, 1.3*inch, 1.3*inch, 1.3*inch])
        activity_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(activity_table)

    elements.append(Spacer(1, 0.2*inch))

    # ==================
    # TOP 10 HOLDERS
    # ==================
    holders_heading = Paragraph("<b>🏆 Top 10 Shareholders</b>", heading_style)
    elements.append(holders_heading)

    if len(top_holders_df) > 0:
        # Calculate total outstanding for percentages
        total_outstanding = 39882500

        holders_data = [['Rank', 'Holder Name', 'Type', 'Best Estimate', '% of Co.']]
        for idx, row in top_holders_df.head(10).iterrows():
            holders_data.append([
                str(idx + 1),
                row['holder_name'][:30],  # Truncate long names
                row['holder_type'][:12],
                f"{int(row['best_estimate']):,}",
                f"{(row['best_estimate'] / total_outstanding * 100):.2f}%"
            ])

        holders_table = Table(holders_data, colWidths=[0.4*inch, 2.2*inch, 0.9*inch, 1.2*inch, 0.7*inch])
        holders_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('ALIGN', (1, 0), (2, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(holders_table)

    # ==================
    # FOOTER
    # ==================
    elements.append(Spacer(1, 0.3*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey
    )
    footer = Paragraph(
        "<b>Data Sources:</b> Share register + SEC 13D/13G filings | "
        "<b>Note:</b> When a holder appears in both sources, we use the higher number to avoid double-counting. | "
        "<b>Contact:</b> shareholderservices@northwind.example.com",
        footer_style
    )
    elements.append(footer)

    # Build PDF
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes
