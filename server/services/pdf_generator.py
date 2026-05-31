"""
PDF Generator — Professional clinical report PDF export using reportlab.
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

RISK_COLORS = {
    "normal":   colors.HexColor("#2e7d32"),
    "monitor":  colors.HexColor("#f9a825"),
    "referral": colors.HexColor("#c62828"),
}

RISK_BG = {
    "normal":   colors.HexColor("#e8f5e9"),
    "monitor":  colors.HexColor("#fff8e1"),
    "referral": colors.HexColor("#ffebee"),
}

RISK_LABELS = {
    "normal":   "NORMAL",
    "monitor":  "MONITOR",
    "referral": "REFERRAL",
}

RISK_LABELS_ID = {
    "normal":   "Normal",
    "monitor":  "Waspadai (Monitor)",
    "referral": "Rujukan (Referral)",
}


def _risk_styled(name: str, val: str):
    fg = RISK_COLORS.get(val, colors.black)
    return f'<font color="{fg.hexval()}">{RISK_LABELS.get(val, val.upper())}</font>'


def generate_report_pdf(report_data: dict) -> bytes:
    """Generate PDF from report dict. Returns PDF bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "HeaderTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1565c0"),
        spaceAfter=4,
        alignment=TA_CENTER,
    ))
    styles.add(ParagraphStyle(
        "HeaderSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#616161"),
        alignment=TA_CENTER,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1565c0"),
        spaceBefore=14,
        spaceAfter=6,
        borderWidth=0,
    ))
    styles.add(ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
    ))
    styles.add(ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#9e9e9e"),
        alignment=TA_CENTER,
        spaceBefore=20,
    ))
    styles.add(ParagraphStyle(
        "Narrative",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        backColor=colors.HexColor("#f5f5f5"),
        borderWidth=0.5,
        borderColor=colors.HexColor("#bdbdbd"),
        borderPadding=8,
    ))

    elements = []
    is_rehab = report_data.get("instruction", "").startswith("rehab_")

    # ── Header ──
    elements.append(Paragraph("NeuroMotorik Screener", styles["HeaderTitle"]))
    elements.append(Paragraph("Laporan Skrining Klinis", styles["HeaderSub"]))
    ts = report_data.get("timestamp", datetime.now().isoformat())
    try:
        dt = datetime.fromisoformat(ts)
        ts_fmt = dt.strftime("%d %B %Y, %H:%M WIB")
    except (ValueError, TypeError):
        ts_fmt = str(ts)
    elements.append(Paragraph(f"Tanggal: {ts_fmt}", styles["HeaderSub"]))

    # ── Patient / Session Info ──
    pid = report_data.get("patient_id", "-")
    rid = report_data.get("report_id", "-")
    instr = report_data.get("instruction", "-")
    instr_label = report_data.get("instruction_label", instr)
    info_data = [
        ["Patient ID", pid],
        ["Report ID", rid],
        ["Tipe Assessment", instr_label if is_rehab else instr],
    ]
    info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
    info_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#e0e0e0")),
    ]))
    elements.append(info_table)

    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1565c0"), spaceAfter=10))

    if is_rehab:
        _build_rehab_section(elements, report_data, styles)
    else:
        _build_clinical_section(elements, report_data, styles)

    # ── Recommendation ──
    rec = report_data.get("recommendation", "")
    if rec:
        elements.append(Paragraph("Rekomendasi", styles["SectionHead"]))
        rec_val = rec.upper() if rec else ""
        if "REFERRAL" in rec_val or "RUJUKAN" in rec_val:
            rec_fg = RISK_COLORS["referral"]
        elif "MONITOR" in rec_val or "WASPADA" in rec_val:
            rec_fg = RISK_COLORS["monitor"]
        else:
            rec_fg = RISK_COLORS["normal"]
        elements.append(Paragraph(
            f'<font color="{rec_fg.hexval()}"><b>{rec}</b></font>',
            styles["Body"],
        ))

    # ── Narrative ──
    narrative = report_data.get("narrative", "")
    if narrative:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("Naratif", styles["SectionHead"]))
        for line in narrative.split("\n"):
            line = line.strip()
            if line:
                elements.append(Paragraph(line, styles["Narrative"]))

    # ── Disclaimer Footer ──
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#bdbdbd"), spaceAfter=6))
    elements.append(Paragraph(
        "Laporan ini dibuat oleh NeuroMotorik Screener dan bukan pengganti diagnosa medis profesional.",
        styles["Disclaimer"],
    ))

    doc.build(elements)
    return buf.getvalue()


def _build_rehab_section(elements, report_data, styles):
    elements.append(Paragraph("Hasil Latihan Rehabilitasi", styles["SectionHead"]))

    reps = report_data.get("reps", 0)
    score = report_data.get("score", 0)
    dur = report_data.get("duration_s", 0)
    instr_label = report_data.get("instruction_label", report_data.get("instruction", "-"))

    rehab_data = [
        ["Metrik", "Nilai"],
        ["Latihan", instr_label],
        ["Repetisi", str(reps)],
        ["Skor Formasi (%)", str(score)],
        ["Durasi (s)", str(dur)],
    ]
    rehab_table = Table(rehab_data, colWidths=[8 * cm, 8 * cm])
    rehab_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(rehab_table)

    conf = report_data.get("confidence_scores", {})
    if conf:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("Skor Kepercayaan", styles["SectionHead"]))
        conf_data = [["Metrik", "Skor"]]
        for k, v in conf.items():
            conf_data.append([k, f"{v:.1f}%"])
        conf_table = Table(conf_data, colWidths=[8 * cm, 8 * cm])
        conf_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(conf_table)


def _build_clinical_section(elements, report_data, styles):
    # ── Risk Classification Table ──
    elements.append(Paragraph("Klasifikasi Risiko", styles["SectionHead"]))

    risk_levels = report_data.get("risk_levels", {})
    conf_scores = report_data.get("confidence_scores", {})

    risk_headers = ["Kondisi", "Tingkat Risiko", "Skor Kepercayaan"]
    risk_rows = [risk_headers]
    condition_map = {
        "stroke": "Stroke (Asimetri)",
        "parkinson": "Parkinson (Tremor)",
        "sarcopenia": "Sarkopenia (Sit-to-Stand)",
    }
    for key in ["stroke", "parkinson", "sarcopenia"]:
        val = risk_levels.get(key, "normal")
        label = RISK_LABELS_ID.get(val, val)
        fg = RISK_COLORS.get(val, colors.black)
        conf_val = conf_scores.get(key, None)
        conf_str = f"{conf_val * 100:.1f}%" if conf_val is not None else "-"
        risk_rows.append([
            condition_map.get(key, key),
            f'<font color="{fg.hexval()}"><b>{label}</b></font>',
            conf_str,
        ])

    risk_table_data = []
    for i, row in enumerate(risk_rows):
        if i == 0:
            risk_table_data.append(row)
        else:
            risk_table_data.append([
                Paragraph(row[0], styles["Body"]),
                Paragraph(row[1], styles["Body"]),
                row[2],
            ])

    risk_table = Table(risk_table_data, colWidths=[6 * cm, 5 * cm, 5 * cm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for i, row in enumerate(risk_rows[1:], start=1):
        val = risk_levels.get(list(risk_levels.keys())[i - 1] if i - 1 < len(risk_levels) else "", "normal")
        bg = RISK_BG.get(val, colors.white)
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    risk_table.setStyle(TableStyle(style_cmds))
    elements.append(risk_table)

    # ── Key Metrics ──
    metrics = report_data.get("metrics", {})
    if metrics:
        elements.append(Paragraph("Metrik Utama", styles["SectionHead"]))

        metric_rows = [["Parameter", "Nilai"]]

        asym = metrics.get("asymmetry", {})
        if asym:
            metric_rows.append(["ASI (rata-rata)", f"{asym.get('meanASI', '-'):.4f}" if isinstance(asym.get('meanASI'), (int, float)) else "-"])
            metric_rows.append(["ASI (maksimum)", f"{asym.get('maxASI', '-'):.4f}" if isinstance(asym.get('maxASI'), (int, float)) else "-"])
            metric_rows.append(["Sudut Bahu Kiri (°)", f"{asym.get('shoulder_angle_L', '-'):.1f}" if isinstance(asym.get('shoulder_angle_L'), (int, float)) else "-"])
            metric_rows.append(["Sudut Bahu Kanan (°)", f"{asym.get('shoulder_angle_R', '-'):.1f}" if isinstance(asym.get('shoulder_angle_R'), (int, float)) else "-"])
            metric_rows.append(["Asimetri Sudut (°)", f"{asym.get('angle_asymmetry', '-'):.1f}" if isinstance(asym.get('angle_asymmetry'), (int, float)) else "-"])

        tremor = metrics.get("tremor", {})
        if tremor:
            df = tremor.get("dominant_freq_hz")
            amp = tremor.get("amplitude")
            dur_pct = tremor.get("duration_pct")
            metric_rows.append(["Frekuensi Tremor (Hz)", f"{df:.2f}" if df is not None else "-"])
            metric_rows.append(["Amplitudo Tremor", f"{amp:.6f}" if amp is not None else "-"])
            metric_rows.append(["Durasi Tremor (%)", f"{dur_pct:.1f}" if dur_pct is not None else "-"])

        sts = metrics.get("sit_to_stand", {})
        if sts:
            dur_s = sts.get("duration_s")
            vel = sts.get("velocity")
            metric_rows.append(["Durasi Sit-to-Stand (s)", f"{dur_s:.2f}" if dur_s is not None else "-"])
            metric_rows.append(["Kecepatan Sit-to-Stand", f"{vel:.4f}" if vel is not None else "-"])

        metric_table = Table(metric_rows, colWidths=[9 * cm, 7 * cm])
        metric_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bdbdbd")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(metric_table)