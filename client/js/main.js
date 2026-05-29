/**
 * main.js — Complete Application Controller v3.0
 * Features:
 *   1. Sequential Assessment (3-in-1)
 *   2. PDF Report Export (jsPDF + html2canvas)
 *   3. Alert Notification System (Notification API + audio beep)
 */

// ═══ Global State ═══════════════════════════════════════════
const app = {
    ws: null, skeleton: null, charts: null, camera: null,
    mediaStream: null, pose: null,
    isRecording: false, frameCount: 0, sessionId: null,
    startTimestamp: null, currentView: "dashboard",
    fpsCounter: 0, currentFPS: 0,
    _localAngles: { shoulder_angle_L: null, shoulder_angle_R: null },
    // Sequential state
    isSequential: false, seqStep: 0, seqTotal: 3,
    seqReports: [], seqResults: [],
    // Alert state
    alertAudio: null, alertThrottle: {},
};

app.SEQUENCE = [
    { step: 1, instruction: "raise_hands", label: "Angkat Kedua Tangan", desc: "Angkat kedua tangan setinggi bahu", duration: 15 },
    { step: 2, instruction: "stand_still", label: "Berdiri Diam", desc: "Berdiri tegak, tangan direntangkan, tahan posisi", duration: 20 },
    { step: 3, instruction: "sit_to_stand", label: "Duduk ke Berdiri", desc: "Duduk di kursi, lalu berdiri perlahan", duration: 15 },
];

// ═══ Init ═══════════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
    initWebSocket(); initFPSCounter(); loadStats();
    initAlertSystem();
});

function initWebSocket() {
    app.ws = new WSClient();
    app.ws.onStatusChange = (s) => {
        const d = document.getElementById("sb-dot"), t = document.getElementById("sb-text");
        if (s === "connected") { if (d) d.className = "dot dot-green"; if (t) t.textContent = "Online"; }
        else { if (d) d.className = "dot dot-red"; if (t) t.textContent = "Offline"; }
    };
    app.ws.onMetrics = handleMetrics;
    app.ws.onReport = handleReport;
    app.ws.onAck = (a) => { app.sessionId = a.session_id; };
    app.ws.onError = (m) => console.warn("[WS]", m);
    app.ws.connect();
}

function initFPSCounter() {
    setInterval(() => {
        app.currentFPS = app.fpsCounter; app.fpsCounter = 0;
        setText("sb-fps", `FPS: ${app.currentFPS}`);
        setText("sb-ping", `Ping: ${app.ws ? app.ws.getLatency() : "—"} ms`);
        setText("sb-frame", `Frame: ${app.frameCount}`);
    }, 1000);
}

function initAlertSystem() {
    try { app.alertAudio = new AudioContext(); } catch (e) {}
    if ("Notification" in window && Notification.permission === "default") {
        const b = document.getElementById("notif-btn");
        if (b) { b.style.display = "flex"; b.onclick = () => Notification.requestPermission(); }
    }
}

// ═══ Voice Instruction ══════════════════════════════════════
app.lastVoiceAlert = 0;
app.currentAudio = null;

function speakInstruction(text, priority = false) {
    if (!priority && app.currentAudio && !app.currentAudio.paused) return; // Jangan tumpuk jika sedang bicara
    
    if (app.currentAudio) {
        app.currentAudio.pause();
        app.currentAudio.currentTime = 0;
    }
    
    // Proxy request ke backend agar tidak diblokir OpaqueResponseBlocking (ORB) oleh browser
    const backendPort = window.location.port === "5173" || window.location.port === "5500" ? 8765 : (window.location.port || 8765);
    const host = window.location.hostname || "127.0.0.1";
    const url = `http://${host}:${backendPort}/api/tts?text=${encodeURIComponent(text)}`;
    
    app.currentAudio = new Audio(url);
    app.currentAudio.play().catch(e => console.warn("[TTS] Gagal memutar suara:", e));
}

function playBeep(freq = 880, dur = 0.15) {
    if (!app.alertAudio) return;
    try {
        const osc = app.alertAudio.createOscillator();
        const gain = app.alertAudio.createGain();
        osc.connect(gain); gain.connect(app.alertAudio.destination);
        osc.frequency.value = freq; osc.type = "square";
        gain.gain.setValueAtTime(0.1, app.alertAudio.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.001, app.alertAudio.currentTime + dur);
        osc.start(); osc.stop(app.alertAudio.currentTime + dur);
    } catch (e) {}
}

function sendNotification(title, body) {
    if ("Notification" in window && Notification.permission === "granted") {
        new Notification(title, { body, icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><circle cx='12' cy='12' r='10' fill='%23ef4444'/></svg>" });
    }
}

// ═══ View Navigation ═══════════════════════════════════════
app.showView = function(name) {
    app.currentView = name;
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
    const ve = document.getElementById(`view-${name}`);
    if (ve) ve.classList.add("active");
    const nb = document.querySelector(`.nav-item[data-view="${name}"]`);
    if (nb) nb.classList.add("active");
};

// ═══ Stats ═════════════════════════════════════════════════
async function loadStats() {
    try {
        const r = await fetch("/api/dashboard/stats");
        if (!r.ok) return;
        const s = await r.json();
        setText("stat-patients", s.total_patients || 0);
        setText("stat-sessions", s.total_sessions || 0);
        setText("stat-normal", s.risk_distribution?.normal || 0);
        setText("stat-monitor", s.risk_distribution?.monitor || 0);
        setText("stat-referal", s.risk_distribution?.referal || 0);
    } catch (e) { console.warn("Stats:", e); }
}

function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

// ═══ Sequential Assessment ═════════════════════════════════
app.startSequential = async function() {
    const pid = document.getElementById("patient-id").value || `PT-${Date.now()}`;
    app.isSequential = true; app.seqStep = 0; app.seqResults = [];
    app.showView("assessment");
    setText("assess-title", "Full Assessment (3-in-1)");
    setText("assess-patient", `Pasien: ${pid}`);
    // Show step indicator
    const si = document.getElementById("seq-indicator");
    if (si) si.style.display = "flex";
    updateSeqStep(0);
    // Show guide
    const pg = document.getElementById("pose-guide");
    if (pg) pg.classList.remove("hidden");
    // Start first step
    await startSeqStep(pid);
};

async function startSeqStep(pid) {
    if (app.seqStep >= app.seqTotal) { finishSequential(); return; }
    const stepData = app.SEQUENCE[app.seqStep];
    updateSeqStep(app.seqStep);
    // Update guide text and speak
    const gt = document.getElementById("guide-text");
    if (gt) gt.textContent = stepData.desc;
    speakInstruction("Tahap selanjutnya. " + stepData.desc);
    
    // Start session for this step
    const age = document.getElementById("patient-age")?.value || null;
    app.ws.startSession(pid, stepData.instruction, age);
    // Init MediaPipe + charts
    await startSingleAssessment(stepData);
}

function updateSeqStep(step) {
    for (let i = 1; i <= app.seqTotal; i++) {
        const el = document.getElementById(`seq-step-${i}`);
        if (el) {
            el.classList.toggle("active", i === step + 1);
            el.classList.toggle("done", i <= step);
        }
    }
    setText("seq-progress", `${step}/${app.seqTotal}`);
}

function finishSequential() {
    app.isSequential = false;
    app.stopAssessment(); // Matikan kamera setelah semua tahap selesai
    const si = document.getElementById("seq-indicator");
    if (si) si.style.display = "none";
    const pg = document.getElementById("pose-guide");
    if (pg) pg.classList.add("hidden");
    // Send sequential_end to get aggregated report
    app.ws.send({ type: "sequential_end" });
}

// ═══ Report Handler ════════════════════════════════════════
function handleReport(report) {
    console.log("[App] Received report:", report);
    
    // Store for sequential
    if (app.isSequential) {
        app.seqResults.push(report);
        app.seqStep++;
        const pid = document.getElementById("patient-id")?.value || "PT-001";
        setTimeout(() => startSeqStep(pid), 2000);
        return;
    }
    
    // Show single report
    displayReport(report, false);
    app.showView("reports");
    loadStats();
}

function displayReport(report, isAggregated) {
    speakInstruction("Penilaian selesai. Silakan periksa laporan klinis Anda di layar.");
    const el = document.getElementById("report-content");
    const empty = document.getElementById("report-empty");
    if (!el || !empty) return;
    empty.style.display = "none";
    el.style.display = "flex";

    const rl = report.risk_levels || {};
    const riskLabel = (r) => r === "referal" ? "REFERAL" : r === "monitor" ? "MONITOR" : "NORMAL";
    const riskClass = (r) => r === "referal" ? "referal" : r === "monitor" ? "monitor" : "normal";

    // Calculate overall confidence
    const cs = report.confidence_scores || {};
    const overall = cs.overall || Math.round((cs.stroke || 0 + cs.parkinson || 0 + cs.sarcopenia || 0) / 3 * 100) || 0;

    const m = report.metrics || report;
    const asiInfo = isAggregated ? "See step details" : (m.asymmetry?.meanASI || m.meanASI || "-");
    const freqInfo = isAggregated ? "See step details" : (m.tremor?.dominant_freq_hz || m.dominant_freq || "-");
    const stsInfo = isAggregated ? "See step details" : (m.sit_to_stand?.duration_s || m.transition_duration || "-");

    let stepDetails = "";
    if (isAggregated && app.seqResults.length > 0) {
        stepDetails = `<div class="card glass" style="margin-top:12px"><div class="card-header"><h2>Detail per Step</h2></div>`;
        app.seqResults.forEach((r, i) => {
            const srl = r.risk_levels || {};
            stepDetails += `<div style="padding:8px 0;border-bottom:1px solid var(--border)">
                <strong>Step ${i+1}: ${r.instruction || ""}</strong> — 
                Stroke: ${riskLabel(srl.stroke)}, Parkinson: ${riskLabel(srl.parkinson)}, Sarcopenia: ${riskLabel(srl.sarcopenia)}
            </div>`;
        });
        stepDetails += `</div>`;
    }

    el.innerHTML = `
        <div class="report-risks">
            <div class="risk-card glass"><div class="risk-label">Stroke</div><div class="risk-value ${riskClass(rl.stroke)}">${riskLabel(rl.stroke)}</div><div class="risk-sub">ASI: ${asiInfo}</div></div>
            <div class="risk-card glass"><div class="risk-label">Parkinson</div><div class="risk-value ${riskClass(rl.parkinson)}">${riskLabel(rl.parkinson)}</div><div class="risk-sub">Freq: ${freqInfo}</div></div>
            <div class="risk-card glass"><div class="risk-label">Sarcopenia</div><div class="risk-value ${riskClass(rl.sarcopenia)}">${riskLabel(rl.sarcopenia)}</div><div class="risk-sub">Durasi: ${stsInfo}</div></div>
        </div>
        <div class="card glass" style="text-align:center;padding:24px"><div class="risk-label">CONFIDENCE SCORE</div><div style="font-size:48px;font-weight:800;background:linear-gradient(135deg,#3b82f6,#22c55e);-webkit-background-clip:text;-webkit-text-fill-color:transparent">${overall}%</div></div>
        ${stepDetails}
        <div class="card glass"><div class="card-header"><h2>Rekomendasi</h2></div><p style="color:var(--text-secondary);line-height:1.6">${report.recommendation || ""}</p></div>
        <div class="report-narrative glass"><div class="card-header"><h2>Narasi Klinis</h2></div><pre>${report.narrative || ""}</pre></div>
        <div style="text-align:center;padding:16px 0;display:flex;gap:12px;justify-content:center">
            <button class="btn btn-primary" onclick="app.showView('dashboard');loadStats()">Kembali</button>
            <button class="btn btn-danger btn-sm" onclick="exportPDF()">📄 Download PDF</button>
        </div>
    `;
}

// ═══ PDF Export ═════════════════════════════════════════════
async function exportPDF() {
    if (typeof window.jspdf === 'undefined') {
        // Load dynamically
        await Promise.all([
            new Promise(r => { const s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js'; s.onload = r; document.head.appendChild(s); }),
            new Promise(r => { const s = document.createElement('script'); s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js'; s.onload = r; document.head.appendChild(s); }),
        ]);
    }
    const el = document.getElementById("report-content");
    if (!el) return;
    try {
        const canvas = await html2canvas(el, { backgroundColor: "#0f172a", scale: 2 });
        const imgData = canvas.toDataURL("image/png");
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
        const w = pdf.internal.pageSize.getWidth();
        const h = (canvas.height * w) / canvas.width;
        pdf.addImage(imgData, "PNG", 0, 0, w, h);
        pdf.save(`NeuroMotorik_Report_${new Date().toISOString().slice(0,10)}.pdf`);
    } catch (e) {
        alert("PDF export gagal: " + e.message);
    }
}

// ═══ Assessment ═════════════════════════════════════════════
app.startAssessment = async function() {
    const pid = document.getElementById("patient-id").value || `PT-${Date.now()}`;
    const inst = document.getElementById("instruction-select").value;
    app.isSequential = false;
    app.showView("assessment");
    // Hide sequential indicator
    const si = document.getElementById("seq-indicator"); if (si) si.style.display = "none";
    const pg = document.getElementById("pose-guide"); if (pg) pg.classList.add("hidden");
    const labels = { raise_hands: "Angkat Kedua Tangan", stand_still: "Berdiri Diam", sit_to_stand: "Duduk ke Berdiri" };
    setText("assess-title", labels[inst] || inst);
    setText("assess-patient", `Pasien: ${pid}`);
    const sc = document.getElementById("sts-card"); if (sc) sc.style.display = inst === "sit_to_stand" ? "block" : "none";
    // Start session
    const age = document.getElementById("patient-age")?.value || null;
    app.ws.startSession(pid, inst, age);
    
    speakInstruction("Silakan mulai " + (labels[inst] || inst));
    await startSingleAssessment({ instruction: inst, duration: 60 });
};

async function startSingleAssessment(opts) {
    if (app.charts) app.charts.destroy();
    app.charts = new ChartManager();
    app.charts.initASI();
    app.charts.initPSD();
    app.frameCount = 0;
    app.isRecording = true;
    app.startTimestamp = performance.now() / 1000;
    app._localAngles = { shoulder_angle_L: null, shoulder_angle_R: null };
    await initMediaPipe(opts.instruction);
    updateTimer(opts.duration * 1000);
}

function updateTimer(maxMs) {
    if (!app.isRecording) return;
    const elapsed = performance.now() - app.startTimestamp * 1000;
    const mins = Math.floor(elapsed / 60000).toString().padStart(2, "0");
    const secs = Math.floor((elapsed % 60000) / 1000).toString().padStart(2, "0");
    setText("timer", `${mins}:${secs}`);
    setText("frame-counter", `Frame: ${app.frameCount}`);
    const pct = Math.min(100, (elapsed / maxMs) * 100);
    const bar = document.getElementById("progress-bar"), label = document.getElementById("progress-text");
    if (bar) bar.style.width = pct + "%";
    if (label) label.textContent = Math.round(pct) + "%";
    if (pct >= 100) { 
        app.isRecording = false; // Stop recording to pause engine updates
        if (app.isSequential) {
            // For sequential, just end the session on backend to get the report
            if (app.sessionId) app.ws.endSession(app.sessionId);
        } else {
            app.stopAssessment(); 
        }
        return; 
    }
    requestAnimationFrame(() => updateTimer(maxMs));
}

// ═══ MediaPipe ═════════════════════════════════════════════
async function initMediaPipe(instruction) {
    // Jika kamera sudah berjalan, jangan re-init (mencegah kamera mati saat transisi 3-in-1)
    if (app.camera && app.pose) {
        return;
    }
    
    const ve = document.getElementById("webcam"), ce = document.getElementById("skeleton-canvas");
    app.skeleton = new SkeletonRenderer(ve, ce);
    if (app.pose) { try { app.pose.close(); } catch (e) {} app.pose = null; }
    const pose = new Pose({ locateFile: (f) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${f}` });
    pose.setOptions({ modelComplexity: 1, smoothLandmarks: true, enableSegmentation: false, minDetectionConfidence: 0.6, minTrackingConfidence: 0.6 });
    pose.onResults((r) => {
        if (!app.isRecording) return;
        app.fpsCounter++;
        
        if (!r.poseLandmarks || r.poseLandmarks.length === 0) {
            // Tangan atau badan tidak terdeteksi sama sekali!
            const now = performance.now();
            if (now - app.lastVoiceAlert > 10000) { // 10 detik cooldown
                speakInstruction("Mohon posisikan badan Anda agar terlihat jelas di depan kamera", true);
                app.lastVoiceAlert = now;
            }
            return;
        }

        const lms = r.poseLandmarks.map((lm, i) => ({ id: i, x: lm.x, y: lm.y, z: lm.z, vis: lm.visibility !== undefined ? lm.visibility : 1.0 }));
        
        // Peringatan jika tangan (pergelangan) tidak terlihat (visibilitas sangat rendah)
        const leftWrist = lms[15], rightWrist = lms[16];
        if (leftWrist && rightWrist && (leftWrist.vis < 0.2 || rightWrist.vis < 0.2)) {
            const now = performance.now();
            if (now - app.lastVoiceAlert > 8000) {
                speakInstruction("Tangan Anda tidak terlihat di kamera. Mundur sedikit atau sesuaikan kamera.", true);
                app.lastVoiceAlert = now;
            }
        }
        
        app.skeleton.draw(lms, app._localAngles);
        app.frameCount++;
        app.ws.sendLandmarks(app.frameCount, performance.now() / 1000, lms);
    });
    await pose.initialize();
    app.pose = pose;
    try {
        if (!window.Camera) throw new Error("CameraUtils not loaded");
        app.camera = new Camera(ve, { onFrame: async () => { if (app.isRecording && app.pose) await app.pose.send({ image: ve }); }, width: 640, height: 480 });
        await app.camera.start();
    } catch (e) { console.error("Camera:", e); alert("Tidak dapat mengakses kamera: " + e.message); app.stopAssessment(); }
}

// ═══ Metrics Handler ════════════════════════════════════════
function handleMetrics(m) {
    if (m.shoulder_angle_L != null) app._localAngles.shoulder_angle_L = m.shoulder_angle_L;
    if (m.shoulder_angle_R != null) app._localAngles.shoulder_angle_R = m.shoulder_angle_R;
    if (m.ASI != null) { setText("asi-value", m.ASI.toFixed(3)); if (app.charts) app.charts.updateASI(m.frame, m.ASI); }
    if (m.shoulder_angle_L != null) setText("angle-L", m.shoulder_angle_L.toFixed(1));
    if (m.shoulder_angle_R != null) setText("angle-R", m.shoulder_angle_R.toFixed(1));
    if (m.dominant_freq_hz != null) setText("freq-dom", m.dominant_freq_hz.toFixed(1));
    if (m.tremor_amplitude != null) setText("tremor-amp", m.tremor_amplitude.toFixed(4));
    if (m.psd_freqs && m.psd_power && app.charts) app.charts.updatePSD(m.psd_freqs, m.psd_power);
    if (m.confidence != null) {
        const ce = document.getElementById("confidence-value"), cb = document.getElementById("confidence-fill");
        if (ce) ce.textContent = Math.round(m.confidence * 100) + "%";
        if (cb) cb.style.width = Math.round(m.confidence * 100) + "%";
    }

    // Voice Alert Handling
    if (m.alert) {
        const now = performance.now();
        if (now - app.lastVoiceAlert > 6000) { // 6 detik cooldown
            if (m.alert === "stroke_alert") {
                speakInstruction("Peringatan, asimetri terdeteksi. Usahakan angkat kedua tangan Anda lebih tegak dan sejajar.", true);
            } else if (m.alert === "stroke_warning") {
                speakInstruction("Angkat sedikit lagi agar posisi tangan lebih sejajar.", true);
            }
            app.lastVoiceAlert = now;
        }
    }
    
    // Sit-to-stand voice feedback
    if (m.sts_phase && m.sts_phase !== app.lastStsPhase) {
        if (m.sts_phase === "standing" && app.lastStsPhase === "transition") {
            speakInstruction("Bagus, sekarang silakan duduk kembali.");
        } else if (m.sts_phase === "sitting" && app.lastStsPhase === "transition") {
            speakInstruction("Bagus, silakan berdiri kembali.");
        }
        app.lastStsPhase = m.sts_phase;
    }
    
    // Sit-to-stand
    if (m.sts_phase) { ["ph-sitting","ph-transition","ph-standing"].forEach(id => { const el = document.getElementById(id); if (el) el.classList.remove("active"); }); const map = { sitting:"ph-sitting", transition:"ph-transition", standing:"ph-standing" }; if (map[m.sts_phase]) { const el = document.getElementById(map[m.sts_phase]); if (el) el.classList.add("active"); } }
    if (m.sts_duration != null) setText("sts-dur", m.sts_duration.toFixed(2) + " s");
    // Alert logic
    if (m.ASI != null && m.ASI > 0.15 && !app.alertThrottle["asi"]) {
        app.alertThrottle["asi"] = true;
        playBeep(1200, 0.2); sendNotification("⚠️ Alert Asimetri", "ASI: " + m.ASI.toFixed(3) + " — melebihi threshold");
        setTimeout(() => delete app.alertThrottle["asi"], 5000);
    }
    if (m.ASI != null && m.ASI > 0.08 && m.ASI <= 0.15 && !app.alertThrottle["asi_warn"]) {
        app.alertThrottle["asi_warn"] = true;
        playBeep(600, 0.15);
        setTimeout(() => delete app.alertThrottle["asi_warn"], 8000);
    }
    // Status badge
    const badge = document.getElementById("status-badge"), stxt = document.getElementById("status-text");
    if (badge && stxt) {
        if (m.status === "alert_asymmetry" || m.status === "alert_slow") { badge.className = "status-overlay alert"; stxt.textContent = "Alert"; }
        else if (m.ASI != null && m.ASI > 0.08) { badge.className = "status-overlay warning"; stxt.textContent = "Waspada"; }
        else { badge.className = "status-overlay normal"; stxt.textContent = "Normal"; }
    }
}

// ═══ Stop ══════════════════════════════════════════════════
app.stopAssessment = function() {
    app.isRecording = false;
    if (app.mediaStream) { app.mediaStream.getTracks().forEach(t => t.stop()); app.mediaStream = null; }
    if (app.pose) { try { app.pose.close(); } catch(e) {} app.pose = null; }
    if (app.skeleton) app.skeleton.clear();
    const ve = document.getElementById("webcam"); if (ve) ve.srcObject = null;
    if (app.sessionId) app.ws.endSession(app.sessionId);
};