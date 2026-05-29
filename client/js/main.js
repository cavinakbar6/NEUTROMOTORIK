/**
 * main.js — Application Controller.
 * Menghubungkan WebSocket, MediaPipe, Charts, Skeleton, dan UI views.
 *
 * Perbaikan:
 *   1. Fix skeleton draw format: convert poseLandmarks ke {id,x,y,z,vis}
 *   2. Fix MediaPipe memory leak: dispose pose + camera on stop
 *   3. Add PSD chart update dari metrics
 *   4. Fix angle data: use local cache per frame (no race condition)
 *   5. Fix API URL: relative path (served dari FastAPI static)
 *   6. Add age parameter support
 *   7. Add confidence display
 */

// ═══ Global State ═══════════════════════════════════════════
const app = {
    ws: null,
    skeleton: null,
    charts: null,
    camera: null,
    mediaStream: null,
    pose: null, // Keep reference for cleanup

    isRecording: false,
    frameCount: 0,
    sessionId: null,
    startTimestamp: null,
    currentView: "dashboard",

    fpsCounter: 0,
    currentFPS: 0,

    // Local angle cache (updated per frame, no race condition)
    _localAngles: {
        shoulder_angle_L: null,
        shoulder_angle_R: null,
    },
};

// ═══ Initialization ════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
    initWebSocket();
    initFPSCounter();
    loadStats();
});

function initWebSocket() {
    app.ws = new WSClient();

    app.ws.onStatusChange = (status) => {
        const dot = document.getElementById("sb-dot");
        const txt = document.getElementById("sb-text");
        const connDot = document.querySelector(".conn-dot");
        const connTxt = document.getElementById("conn-text");
        const serverEl = document.getElementById("sb-server");

        if (status === "connected") {
            if (dot) { dot.className = "dot dot-green"; }
            if (txt) { txt.textContent = "Online"; }
            if (connDot) { connDot.classList.add("connected"); }
            if (connTxt) { connTxt.textContent = "Connected"; }
            if (serverEl) { serverEl.textContent = "Server: OK"; }
        } else {
            if (dot) { dot.className = "dot dot-red"; }
            if (txt) { txt.textContent = "Offline"; }
            if (connDot) { connDot.classList.remove("connected"); }
            if (connTxt) { connTxt.textContent = "Disconnected"; }
            if (serverEl) { serverEl.textContent = "Server: —"; }
        }
    };

    app.ws.onMetrics = handleMetrics;
    app.ws.onReport = handleReport;
    app.ws.onAck = (a) => {
        app.sessionId = a.session_id;
        console.log("[App] Session:", app.sessionId);
    };
    app.ws.onError = (msg) => {
        console.warn("[App] Server error:", msg);
    };

    app.ws.connect();
}

function initFPSCounter() {
    setInterval(() => {
        app.currentFPS = app.fpsCounter;
        app.fpsCounter = 0;
        const fpsEl = document.getElementById("sb-fps");
        const pingEl = document.getElementById("sb-ping");
        const frameEl = document.getElementById("sb-frame");
        if (fpsEl) fpsEl.textContent = `FPS: ${app.currentFPS}`;
        if (pingEl) pingEl.textContent = `Ping: ${app.ws ? app.ws.getLatency() : "—"} ms`;
        if (frameEl) frameEl.textContent = `Frame: ${app.frameCount}`;
    }, 1000);
}

// ═══ View Navigation ═══════════════════════════════════════
app.showView = function(name) {
    app.currentView = name;

    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));

    const viewEl = document.getElementById(`view-${name}`);
    if (viewEl) viewEl.classList.add("active");

    const navBtn = document.querySelector(`.nav-item[data-view="${name}"]`);
    if (navBtn) navBtn.classList.add("active");
};

// ═══ Stats ═════════════════════════════════════════════════
async function loadStats() {
    try {
        // Relative URL — works when served from FastAPI static files
        const resp = await fetch("/api/dashboard/stats");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const s = await resp.json();
        setText("stat-patients", s.total_patients || 0);
        setText("stat-sessions", s.total_sessions || 0);
        setText("stat-normal", s.risk_distribution?.normal || 0);
        setText("stat-monitor", s.risk_distribution?.monitor || 0);
        setText("stat-referal", s.risk_distribution?.referal || 0);
    } catch (e) {
        console.warn("Stats load failed:", e);
    }
}

function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
}

// ═══ Start Assessment ══════════════════════════════════════
app.startAssessment = async function() {
    const patientId = document.getElementById("patient-id").value || `PT-${Date.now()}`;
    const instruction = document.getElementById("instruction-select").value;
    const ageInput = document.getElementById("patient-age");
    const age = ageInput ? ageInput.value : null;

    // Switch to assessment view
    app.showView("assessment");

    // Update UI
    const instructLabel = {
        raise_hands: "Angkat Kedua Tangan",
        stand_still: "Berdiri Diam",
        sit_to_stand: "Duduk ke Berdiri",
    };
    setText("assess-title", instructLabel[instruction] || instruction);
    setText("assess-patient", `Pasien: ${patientId}`);

    // Show/hide STS card
    const stsCard = document.getElementById("sts-card");
    if (stsCard) stsCard.style.display = instruction === "sit_to_stand" ? "block" : "none";

    // Init charts
    if (app.charts) app.charts.destroy();
    app.charts = new ChartManager();
    app.charts.initASI();
    app.charts.initPSD();

    // Start session on server (with age for sarcopenia thresholds)
    app.ws.startSession(patientId, instruction, age);

    // Reset state BEFORE initMediaPipe so the frame loop runs
    app.frameCount = 0;
    app.isRecording = true;
    app.startTimestamp = performance.now() / 1000;
    app._localAngles = { shoulder_angle_L: null, shoulder_angle_R: null };

    // Init MediaPipe
    await initMediaPipe(instruction);

    updateTimer();
};

// ═══ MediaPipe + Camera ════════════════════════════════════
async function initMediaPipe(instruction) {
    const videoEl = document.getElementById("webcam");
    const canvasEl = document.getElementById("skeleton-canvas");
    app.skeleton = new SkeletonRenderer(videoEl, canvasEl);

    // Cleanup previous instances
    if (app.camera) {
        app.camera.stop();
        app.camera = null;
    }
    if (app.pose) {
        try { app.pose.close(); } catch(e) {}
        app.pose = null;
    }

    // Configure AI (MediaPipe Pose)
    const pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
    });

    pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        enableSegmentation: false,
        minDetectionConfidence: 0.6,
        minTrackingConfidence: 0.6,
    });

    pose.onResults((results) => {
        if (!app.isRecording) return;
        app.fpsCounter++;

        if (results.poseLandmarks) {
            const normalizedLandmarks = results.poseLandmarks.map((lm, i) => ({
                id: i,
                x: lm.x,
                y: lm.y,
                z: lm.z,
                vis: lm.visibility || 0,
            }));

            // Draw skeleton with local angle cache
            app.skeleton.draw(normalizedLandmarks, app._localAngles);

            // Send to server
            app.frameCount++;
            app.ws.sendLandmarks(app.frameCount, performance.now() / 1000, normalizedLandmarks);
        } else {
            // No person detected, clear skeleton
            app.skeleton.ctx.clearRect(0, 0, app.skeleton.canvas.width, app.skeleton.canvas.height);
        }
    });

    // Start loading AI model in the background (Non-blocking)
    const initializePose = async () => {
        try {
            await pose.initialize();
            app.pose = pose; 
            console.log("[MediaPipe] AI Model Loaded Successfully");
        } catch (e) {
            console.error("Pose initialization failed:", e);
            alert("Gagal memuat model AI (MediaPipe). Periksa koneksi internet Anda.");
            app.stopAssessment();
        }
    };
    initializePose();

    // Setup and start Camera using Official MediaPipe Utility
    // This automatically handles permissions, getUserMedia, and requestVideoFrameCallback
    try {
        if (!window.Camera) {
            throw new Error("Library CameraUtils tidak ditemukan. Pastikan koneksi internet aktif untuk download CDN.");
        }
        
        app.camera = new Camera(videoEl, {
            onFrame: async () => {
                if (app.isRecording && app.pose) {
                    await app.pose.send({ image: videoEl });
                }
            },
            width: 640,
            height: 480
        });
        
        await app.camera.start();
        
    } catch (e) {
        console.error("Camera access failed:", e);
        alert("Tidak dapat mengakses kamera:\n" + e.message + "\n\nPastikan izin diberikan dan buka web ini di http://localhost:8765");
        app.stopAssessment();
    }
}

// ═══ Timer ═════════════════════════════════════════════════
function updateTimer() {
    if (!app.isRecording) return;
    const elapsed = performance.now() / 1000 - app.startTimestamp;
    const mins = Math.floor(elapsed / 60).toString().padStart(2, "0");
    const secs = Math.floor(elapsed % 60).toString().padStart(2, "0");

    setText("timer", `${mins}:${secs}`);
    setText("frame-counter", `Frame: ${app.frameCount}`);

    const pct = Math.min(100, (elapsed / 60) * 100);
    const bar = document.getElementById("progress-bar");
    const label = document.getElementById("progress-text");
    if (bar) bar.style.width = pct + "%";
    if (label) label.textContent = Math.round(pct) + "%";

    // Auto-stop at 60 seconds
    if (pct >= 100) {
        app.stopAssessment();
        return;
    }

    requestAnimationFrame(updateTimer);
}

// ═══ Handle Metrics ════════════════════════════════════════
function handleMetrics(m) {
    // Update local angle cache for skeleton (solves race condition)
    if (m.shoulder_angle_L != null) app._localAngles.shoulder_angle_L = m.shoulder_angle_L;
    if (m.shoulder_angle_R != null) app._localAngles.shoulder_angle_R = m.shoulder_angle_R;

    // ASI
    if (m.ASI != null) {
        setText("asi-value", m.ASI.toFixed(3));
        if (app.charts) app.charts.updateASI(m.frame, m.ASI);

        // Badge — using evidence-based thresholds
        const badge = document.getElementById("asi-badge");
        if (badge) {
            if (m.ASI > 0.15) { badge.className = "mc-badge alert"; badge.textContent = "Alert"; }
            else if (m.ASI > 0.08) { badge.className = "mc-badge warning"; badge.textContent = "Waspada"; }
            else { badge.className = "mc-badge normal"; badge.textContent = "Normal"; }
        }
    }

    // Angles
    if (m.shoulder_angle_L != null) setText("angle-L", m.shoulder_angle_L.toFixed(1));
    if (m.shoulder_angle_R != null) setText("angle-R", m.shoulder_angle_R.toFixed(1));

    // Tremor
    if (m.dominant_freq_hz != null) setText("freq-dom", m.dominant_freq_hz.toFixed(1));
    if (m.tremor_amplitude != null) setText("tremor-amp", m.tremor_amplitude.toFixed(4));

    // PSD Chart — NOW ACTUALLY UPDATED!
    if (m.psd_freqs && m.psd_power && app.charts) {
        app.charts.updatePSD(m.psd_freqs, m.psd_power);
    }

    // Sit-to-stand
    if (m.sts_phase) {
        ["ph-sitting", "ph-transition", "ph-standing"].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.remove("active");
        });
        const map = { sitting: "ph-sitting", transition: "ph-transition", standing: "ph-standing" };
        if (map[m.sts_phase]) {
            const el = document.getElementById(map[m.sts_phase]);
            if (el) el.classList.add("active");
        }
    }
    if (m.sts_duration != null) setText("sts-dur", m.sts_duration.toFixed(2) + " s");

    // Confidence indicator
    if (m.confidence != null) {
        const confEl = document.getElementById("confidence-value");
        const confBar = document.getElementById("confidence-fill");
        if (confEl) confEl.textContent = Math.round(m.confidence * 100) + "%";
        if (confBar) confBar.style.width = Math.round(m.confidence * 100) + "%";
    }

    // Status badge on video
    const badge = document.getElementById("status-badge");
    const stxt = document.getElementById("status-text");
    if (badge && stxt) {
        if (m.status === "alert_asymmetry" || m.status === "alert_slow") {
            badge.className = "status-overlay alert";
            stxt.textContent = "Alert";
        } else if (m.ASI != null && m.ASI > 0.08) {
            badge.className = "status-overlay warning";
            stxt.textContent = "Waspada";
        } else {
            badge.className = "status-overlay normal";
            stxt.textContent = "Normal";
        }
    }
}

// ═══ Stop Assessment ═══════════════════════════════════════
app.stopAssessment = function() {
    app.isRecording = false;

    // Stop camera tracks
    if (app.mediaStream) {
        app.mediaStream.getTracks().forEach(t => t.stop());
        app.mediaStream = null;
    }

    // Cleanup MediaPipe Pose (prevent memory leak)
    if (app.pose) {
        try { app.pose.close(); } catch(e) {}
        app.pose = null;
    }

    // Clear skeleton
    if (app.skeleton) app.skeleton.clear();

    // Clear video element
    const videoEl = document.getElementById("webcam");
    if (videoEl) videoEl.srcObject = null;

    // Send session_end
    if (app.sessionId) {
        app.ws.endSession(app.sessionId);
    }
};

// ═══ Handle Report ═════════════════════════════════════════
function handleReport(report) {
    console.log("[App] Report:", report);

    const el = document.getElementById("report-content");
    const empty = document.getElementById("report-empty");
    if (!el || !empty) return;

    empty.style.display = "none";
    el.style.display = "flex";

    const m = report.metrics || {};
    const rl = report.risk_levels || {};
    const riskLabel = (r) => {
        if (r === "referal") return "REFERAL";
        if (r === "monitor") return "MONITOR";
        return "NORMAL";
    };
    const riskClass = (r) => {
        if (r === "referal") return "referal";
        if (r === "monitor") return "monitor";
        return "normal";
    };

    // Build ASI detail
    const asiDetail = m.asymmetry || {};
    const asiText = asiDetail.meanASI != null ? asiDetail.meanASI.toFixed(4) : "-";
    const angleAsymText = asiDetail.angle_asymmetry != null ? asiDetail.angle_asymmetry.toFixed(1) : "-";

    // Build tremor detail
    const tremorDetail = m.tremor || {};
    const freqText = tremorDetail.dominant_freq_hz != null ? tremorDetail.dominant_freq_hz.toFixed(2) : "-";
    const durPctText = tremorDetail.duration_pct != null ? tremorDetail.duration_pct.toFixed(1) : "-";

    // Build STS detail
    const stsDetail = m.sit_to_stand || {};
    const stsDurText = stsDetail.duration_s != null ? stsDetail.duration_s.toFixed(2) : "-";

    el.innerHTML = `
        <div class="report-risks">
            <div class="risk-card glass">
                <div class="risk-label">Stroke (Asimetri)</div>
                <div class="risk-value ${riskClass(rl.stroke)}">${riskLabel(rl.stroke)}</div>
                <div class="risk-sub">ASI: ${asiText} | Δ Sudut: ${angleAsymText}&deg;</div>
            </div>
            <div class="risk-card glass">
                <div class="risk-label">Parkinson (Tremor)</div>
                <div class="risk-value ${riskClass(rl.parkinson)}">${riskLabel(rl.parkinson)}</div>
                <div class="risk-sub">Freq: ${freqText} Hz | Durasi: ${durPctText}%</div>
            </div>
            <div class="risk-card glass">
                <div class="risk-label">Sarcopenia (STS)</div>
                <div class="risk-value ${riskClass(rl.sarcopenia)}">${riskLabel(rl.sarcopenia)}</div>
                <div class="risk-sub">Durasi: ${stsDurText} s</div>
            </div>
        </div>

        <div class="card glass">
            <div class="card-header"><h2>Rekomendasi</h2></div>
            <p style="color:var(--text-secondary);line-height:1.7;font-size:14px">${report.recommendation || ""}</p>
        </div>

        <div class="report-narrative glass">
            <div class="card-header"><h2>Narasi Klinis</h2></div>
            <pre>${report.narrative || ""}</pre>
        </div>

        <div style="text-align:center;padding:16px 0">
            <button class="btn btn-primary" onclick="app.showView('dashboard');loadStats();document.getElementById('report-empty').style.display='flex';document.getElementById('report-content').style.display='none'">
                Kembali ke Dashboard
            </button>
        </div>
    `;

    // Switch to reports view
    app.showView("reports");
    loadStats();
}
