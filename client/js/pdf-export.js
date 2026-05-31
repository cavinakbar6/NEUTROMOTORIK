/**
 * PDF Export — Client-side PDF generation using jsPDF as a fallback.
 * Generates a simple clinical report PDF in the browser.
 */

const RISK_COLORS = {
  normal: { fg: [46, 125, 50], bg: [232, 245, 233] },
  monitor: { fg: [249, 168, 37], bg: [255, 248, 225] },
  referral: { fg: [198, 40, 40], bg: [255, 235, 238] },
};

const RISK_LABELS = {
  normal: "Normal",
  monitor: "Waspadai (Monitor)",
  referral: "Rujukan (Referral)",
};

const CONDITION_LABELS = {
  stroke: "Stroke (Asimetri)",
  parkinson: "Parkinson (Tremor)",
  sarcopenia: "Sarkopenia (Sit-to-Stand)",
};

/**
 * Generate and download a PDF report from report data.
 * @param {Object} reportData - The report dict returned by the API.
 */
function exportReportPDF(reportData) {
  if (typeof jspdf === "undefined" && typeof window.jspdf === "undefined") {
    alert("jsPDF tidak ditemukan. Pastikan library sudah dimuat.");
    return;
  }

  const { jsPDF } = typeof window.jspdf !== "undefined" ? window.jspdf : { jsPDF: jspdf };
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const pageW = doc.internal.pageSize.getWidth();
  const margin = 20;
  const contentW = pageW - margin * 2;
  let y = margin;

  const isRehab = (reportData.instruction || "").startsWith("rehab_");

  // ── Helper ──
  function setColor(rgb) {
    doc.setTextColor(rgb[0], rgb[1], rgb[2]);
  }

  function addSection(title) {
    y += 8;
    if (y > 260) { doc.addPage(); y = margin; }
    doc.setFontSize(13);
    setColor([21, 101, 192]);
    doc.text(title, margin, y);
    doc.setDrawColor(21, 101, 192);
    doc.setLineWidth(0.5);
    doc.line(margin, y + 2, margin + contentW, y + 2);
    y += 6;
  }

  // ── Header ──
  doc.setFontSize(18);
  setColor([21, 101, 192]);
  doc.text("NeuroMotorik Screener", pageW / 2, y, { align: "center" });
  y += 7;
  doc.setFontSize(11);
  setColor([97, 97, 97]);
  doc.text("Laporan Skrining Klinis", pageW / 2, y, { align: "center" });
  y += 6;

  let ts = reportData.timestamp || new Date().toISOString();
  try {
    const d = new Date(ts);
    ts = d.toLocaleDateString("id-ID", { day: "numeric", month: "long", year: "numeric" })
      + ", " + d.toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" });
  } catch (e) { /* keep original */ }
  doc.setFontSize(9);
  doc.text("Tanggal: " + ts, pageW / 2, y, { align: "center" });
  y += 8;

  // ── Patient Info ──
  doc.setDrawColor(189, 189, 189);
  doc.setLineWidth(0.3);
  doc.line(margin, y, margin + contentW, y);
  y += 5;

  const infoFields = [
    ["Patient ID", reportData.patient_id || "-"],
    ["Report ID", reportData.report_id || "-"],
    ["Tipe Assessment", isRehab ? (reportData.instruction_label || reportData.instruction) : (reportData.instruction || "-")],
  ];
  doc.setFontSize(10);
  infoFields.forEach(([label, value]) => {
    setColor([0, 0, 0]);
    doc.setFont(undefined, "bold");
    doc.text(label + ":", margin, y);
    doc.setFont(undefined, "normal");
    doc.text(String(value), margin + 40, y);
    y += 5;
  });

  if (isRehab) {
    _buildRehabSection(doc, reportData, margin, contentW, y, addSection, setColor);
  } else {
    _buildClinicalSection(doc, reportData, margin, contentW, y, addSection, setColor);
  }

  // ── Disclaimer ──
  doc.setFontSize(7);
  setColor([158, 158, 158]);
  doc.text(
    "Laporan ini dibuat oleh NeuroMotorik Screener dan bukan pengganti diagnosa medis profesional.",
    pageW / 2, 285, { align: "center" }
  );

  // ── Save ──
  const filename = `neuromotorik-report-${reportData.report_id || "export"}.pdf`;
  doc.save(filename);
}

function _buildRehabSection(doc, reportData, margin, contentW, startY, addSection, setColor) {
  let y = startY;
  addSection("Hasil Latihan Rehabilitasi");

  const rehabData = [
    ["Metrik", "Nilai"],
    ["Latihan", reportData.instruction_label || reportData.instruction || "-"],
    ["Repetisi", String(reportData.reps || 0)],
    ["Skor Formasi (%)", String(reportData.score || 0)],
    ["Durasi (s)", String(reportData.duration_s || 0)],
  ];

  doc.setFontSize(10);
  doc.setFont(undefined, "bold");
  setColor([255, 255, 255]);
  doc.setFillColor(21, 101, 192);
  doc.rect(margin, y, contentW, 7, "F");
  doc.text(rehabData[0][0], margin + 3, y + 5);
  doc.text(rehabData[0][1], margin + contentW / 2 + 3, y + 5);
  y += 7;
  doc.setFont(undefined, "normal");
  setColor([0, 0, 0]);

  for (let i = 1; i < rehabData.length; i++) {
    if (i % 2 === 0) {
      doc.setFillColor(245, 245, 245);
      doc.rect(margin, y, contentW, 6, "F");
    }
    doc.setFont(undefined, "bold");
    doc.text(rehabData[i][0], margin + 3, y + 4.5);
    doc.setFont(undefined, "normal");
    doc.text(rehabData[i][1], margin + contentW / 2 + 3, y + 4.5);
    y += 6;
  }

  // Confidence scores
  const conf = reportData.confidence_scores || {};
  if (Object.keys(conf).length > 0) {
    y += 4;
    addSection("Skor Kepercayaan");
    doc.setFont(undefined, "bold");
    setColor([255, 255, 255]);
    doc.setFillColor(21, 101, 192);
    doc.rect(margin, y, contentW, 7, "F");
    doc.text("Metrik", margin + 3, y + 5);
    doc.text("Skor", margin + contentW / 2 + 3, y + 5);
    y += 7;
    doc.setFont(undefined, "normal");
    setColor([0, 0, 0]);
    let idx = 0;
    for (const [k, v] of Object.entries(conf)) {
      if (idx % 2 === 1) {
        doc.setFillColor(245, 245, 245);
        doc.rect(margin, y, contentW, 6, "F");
      }
      doc.setFont(undefined, "bold");
      doc.text(k, margin + 3, y + 4.5);
      doc.setFont(undefined, "normal");
      doc.text((typeof v === "number" ? v.toFixed(1) + "%" : String(v)), margin + contentW / 2 + 3, y + 4.5);
      y += 6;
      idx++;
    }
  }
}

function _buildClinicalSection(doc, reportData, margin, contentW, startY, addSection, setColor) {
  let y = startY;

  // ── Risk Classification ──
  addSection("Klasifikasi Risiko");

  const riskLevels = reportData.risk_levels || {};
  const confScores = reportData.confidence_scores || {};

  // Header row
  doc.setFontSize(10);
  doc.setFont(undefined, "bold");
  setColor([255, 255, 255]);
  doc.setFillColor(21, 101, 192);
  doc.rect(margin, y, contentW, 7, "F");
  doc.text("Kondisi", margin + 3, y + 5);
  doc.text("Tingkat Risiko", margin + 55, y + 5);
  doc.text("Skor Kepercayaan", margin + contentW - 35, y + 5);
  y += 7;

  doc.setFont(undefined, "normal");
  const keys = ["stroke", "parkinson", "sarcopenia"];
  keys.forEach((key, i) => {
    const val = riskLevels[key] || "normal";
    const c = RISK_COLORS[val] || RISK_COLORS.normal;
    const label = RISK_LABELS[val] || val;
    const condLabel = CONDITION_LABELS[key] || key;
    const confVal = confScores[key];

    doc.setFillColor(c.bg[0], c.bg[1], c.bg[2]);
    doc.rect(margin, y, contentW, 7, "F");

    setColor([0, 0, 0]);
    doc.text(condLabel, margin + 3, y + 5);
    setColor(c.fg);
    doc.setFont(undefined, "bold");
    doc.text(label, margin + 55, y + 5);
    doc.setFont(undefined, "normal");
    setColor([0, 0, 0]);
    doc.text(confVal !== undefined && confVal !== null ? (confVal * 100).toFixed(1) + "%" : "-", margin + contentW - 35, y + 5);
    y += 7;
  });

  // ── Key Metrics ──
  const metrics = reportData.metrics || {};
  if (Object.keys(metrics).length > 0) {
    addSection("Metrik Utama");

    doc.setFont(undefined, "bold");
    setColor([255, 255, 255]);
    doc.setFillColor(21, 101, 192);
    doc.rect(margin, y, contentW, 7, "F");
    doc.text("Parameter", margin + 3, y + 5);
    doc.text("Nilai", margin + contentW - 25, y + 5);
    y += 7;

    doc.setFont(undefined, "normal");
    setColor([0, 0, 0]);
    let rowIdx = 0;

    const asym = metrics.asymmetry || {};
    const tremor = metrics.tremor || {};
    const sts = metrics.sit_to_stand || {};

    const metricEntries = [
      ["ASI (rata-rata)", asym.meanASI],
      ["ASI (maksimum)", asym.maxASI],
      ["Sudut Bahu Kiri (\u00B0)", asym.shoulder_angle_L],
      ["Sudut Bahu Kanan (\u00B0)", asym.shoulder_angle_R],
      ["Asimetri Sudut (\u00B0)", asym.angle_asymmetry],
      ["Frekuensi Tremor (Hz)", tremor.dominant_freq_hz],
      ["Amplitudo Tremor", tremor.amplitude],
      ["Durasi Tremor (%)", tremor.duration_pct],
      ["Durasi Sit-to-Stand (s)", sts.duration_s],
      ["Kecepatan Sit-to-Stand", sts.velocity],
    ];

    metricEntries.forEach(([label, value]) => {
      if (value === undefined || value === null) return;
      if (y > 260) { doc.addPage(); y = margin; }
      if (rowIdx % 2 === 1) {
        doc.setFillColor(245, 245, 245);
        doc.rect(margin, y, contentW, 6, "F");
      }
      doc.setFont(undefined, "bold");
      doc.text(label, margin + 3, y + 4.5);
      doc.setFont(undefined, "normal");
      let valStr = "-";
      if (typeof value === "number") {
        if (Math.abs(value) < 0.01) valStr = value.toFixed(6);
        else if (Math.abs(value) < 1) valStr = value.toFixed(4);
        else valStr = value.toFixed(2);
      } else {
        valStr = String(value);
      }
      doc.text(valStr, margin + contentW - 25, y + 4.5);
      y += 6;
      rowIdx++;
    });
  }

  // ── Recommendation ──
  const rec = reportData.recommendation || "";
  if (rec) {
    addSection("Rekomendasi");
    const recUpper = rec.toUpperCase();
    let recColor = [46, 125, 50]; // normal green
    if (recUpper.includes("REFERRAL") || recUpper.includes("RUJUKAN")) {
      recColor = [198, 40, 40];
    } else if (recUpper.includes("MONITOR") || recUpper.includes("WASPADA")) {
      recColor = [249, 168, 37];
    }
    setColor(recColor);
    doc.setFont(undefined, "bold");
    doc.text(rec, margin, y);
    doc.setFont(undefined, "normal");
    y += 6;
  }

  // ── Narrative ──
  const narrative = reportData.narrative || "";
  if (narrative) {
    addSection("Naratif");
    setColor([0, 0, 0]);
    const lines = narrative.split("\n");
    lines.forEach((line) => {
      line = line.trim();
      if (!line) return;
      if (y > 260) { doc.addPage(); y = margin; }
      const wrapped = doc.splitTextToSize(line, contentW);
      wrapped.forEach((wl) => {
        doc.text(wl, margin, y);
        y += 5;
      });
    });
  }
}

window.exportReportPDF = exportReportPDF;