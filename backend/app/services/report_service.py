from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfgen import canvas


def generate_basic_report(output_path: str | Path, title: str, summary: str) -> Path:
    """Generate a simple PDF verification report."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    report = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter
    report.setTitle(title)
    report.setFont("Helvetica-Bold", 16)
    report.drawString(72, height - 72, title)
    report.setFont("Helvetica", 11)
    report.drawString(72, height - 110, summary)
    report.showPage()
    report.save()
    return path


def generate_verification_report(
    output_path: str | Path,
    verification_data: dict[str, Any],
) -> Path:
    """Generate a recruiter-ready PDF report from a saved verification result."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="DocuVerify AI Verification Report",
    )

    story = [
        Paragraph("DocuVerify AI", styles["Title"]),
        Paragraph("Document Authenticity Verification Report", styles["Heading2"]),
        Paragraph(
            f"Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            styles["Normal"],
        ),
        Spacer(1, 12),
    ]

    summary_rows = [
        ["Document ID", verification_data.get("document_id", "N/A")],
        ["Original filename", verification_data.get("original_filename", "N/A")],
        ["Uploaded by", verification_data.get("uploaded_by", "N/A")],
        ["Verification date", verification_data.get("verification_date", "N/A")],
        ["Authenticity score", f"{verification_data.get('authenticity_score', 0)} / 100"],
        ["Risk level", verification_data.get("risk_level", "N/A")],
        ["Final decision", verification_data.get("final_decision", "N/A")],
    ]
    story.append(build_table(summary_rows))
    story.append(Spacer(1, 14))

    sections = [
        ("Extracted Text Summary", verification_data.get("extracted_text_summary")),
        ("QR Verification Result", verification_data.get("qr_status")),
        ("Hash Verification Result", verification_data.get("hash_status")),
        ("Metadata Analysis Result", verification_data.get("metadata_status")),
        ("Tampering Detection Result", verification_data.get("tampering_status")),
        ("AI Explanation", verification_data.get("ai_explanation")),
        ("Recommendation", verification_data.get("recommendation")),
    ]
    for title, value in sections:
        story.append(Paragraph(title, styles["Heading3"]))
        story.append(Paragraph(safe_text(value), styles["BodyText"]))
        story.append(Spacer(1, 8))

    story.append(Paragraph("Fraud Flags", styles["Heading3"]))
    flags = verification_data.get("fraud_flags") or []
    if flags:
        flag_rows = [["Severity", "Type", "Message"]]
        flag_rows.extend(
            [flag.get("severity", ""), flag.get("flag_type", ""), flag.get("message", "")]
            for flag in flags
        )
        story.append(build_table(flag_rows, header=True))
    else:
        story.append(Paragraph("No fraud flags were saved for this verification.", styles["BodyText"]))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Professional Issue Explanations", styles["Heading3"]))
    explanation_cards = verification_data.get("explanation_cards") or []
    if explanation_cards:
        rows = [["Issue", "Module", "Severity", "Recommended Action"]]
        rows.extend(
            [
                card.get("issue_title", ""),
                card.get("detected_by_module", ""),
                card.get("severity", ""),
                card.get("recommended_action", ""),
            ]
            for card in explanation_cards
        )
        story.append(build_table(rows, header=True))
    else:
        story.append(Paragraph("No issue explanation cards were generated.", styles["BodyText"]))

    document.build(story)
    return path


def build_table(rows: list[list[Any]], header: bool = False) -> Table:
    column_count = max(len(row) for row in rows) if rows else 2
    if column_count == 2:
        widths = [1.8 * inch, 4.6 * inch]
    elif column_count == 4:
        widths = [1.4 * inch, 1.6 * inch, 0.8 * inch, 2.6 * inch]
    else:
        widths = [1.1 * inch, 1.6 * inch, 3.7 * inch]
    wrapped_rows = [
        [Paragraph(safe_text(cell), getSampleStyleSheet()["BodyText"]) for cell in row]
        for row in rows
    ]
    table = Table(wrapped_rows, colWidths=widths[:column_count])
    style = [
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9e2ec")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d9e2ec")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#172026")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")))
    table.setStyle(TableStyle(style))
    return table


def safe_text(value: Any) -> str:
    text = str(value or "Not available")
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:2500]
