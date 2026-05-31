/**
 * simulation.js — Client-side simulation runner for demo/testing without a camera.
 * Provides UI for selecting scenarios and running simulated assessments via REST API.
 */

const SimRunner = {
    active: false,
    polling: null,

    getApiBase() {
        const port = window.location.port === "5173" || window.location.port === "5500" ? 8765 : (window.location.port || 8765);
        const host = window.location.hostname || "127.0.0.1";
        return `http://${host}:${port}/api/sim`;
    },

    init() {
        this.addSimUI();
        this.bindEvents();
    },

    addSimUI() {
        // Panel sudah di-render di HTML, tinggal bind events
        this.bindEvents();
    },

    bindEvents() {
        const btn = document.getElementById("btn-sim-run");
        if (btn) {
            btn.addEventListener("click", () => {
                if (!this.active) this.runSimulation();
            });
        }
    },

    async runSimulation() {
        const btn = document.getElementById("btn-sim-run");
        const resultDiv = document.getElementById("sim-result");
        if (!btn || this.active) return;

        this.active = true;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner" style="display:inline-block;width:16px;height:16px;border:2px solid #fff;border-top-color:transparent;border-radius:50%;animation:spin 0.6s linear infinite"></span> Menjalankan simulasi...';

        const scenario = document.getElementById("sim-scenario").value;
        const instruction = document.getElementById("sim-instruction").value;
        const duration_s = parseFloat(document.getElementById("sim-duration").value) || 15;
        const patient_age = parseInt(document.getElementById("sim-age").value) || 65;

        const body = {
            instruction,
            fps: 30,
            duration_s,
            patient_age,
            scenario,
            noise_level: 0.002,
        };

        try {
            const resp = await fetch(`${this.getApiBase()}/start`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body),
            });

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: resp.statusText }));
                throw new Error(err.detail || "Simulation failed");
            }

            const data = await resp.json();

            // Display report using existing UI
            if (data.report) {
                resultDiv.style.display = "block";
                resultDiv.innerHTML = this.renderReport(data);
                // Also trigger the main app's report handler if available
                if (typeof handleReport === "function") {
                    handleReport(data.report);
                } else if (app.ws && app.ws.onReport) {
                    // Route through the WS handler
                    app.showView("reports");
                    const reportsView = document.getElementById("view-reports");
                    const reportContent = document.getElementById("report-content");
                    const reportEmpty = document.getElementById("report-empty");
                    if (reportContent) {
                        reportContent.innerHTML = this.renderFullReport(data.report);
                        reportContent.style.display = "block";
                    }
                    if (reportEmpty) reportEmpty.style.display = "none";
                }
            }
        } catch (e) {
            resultDiv.style.display = "block";
            resultDiv.innerHTML = `<div style="padding:12px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:8px;color:#fca5a5"><strong>Error:</strong> ${e.message}</div>`;
        } finally {
            this.active = false;
            btn.disabled = false;
            btn.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/></svg> Jalankan Simulasi';
        }
    },

    renderReport(data) {
        const report = data.report;
        const scenarioLabels = {
            normal: "Normal",
            stroke_mild: "Stroke Ringan",
            stroke_severe: "Stroke Berat",
            parkinson_tremor: "Parkinson (Tremor)",
            sarcopenia_slow: "Sarcopenia (STS Lambat)",
        };
        return `
            <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                    <h3 style="margin:0;font-size:15px">Hasil Simulasi</h3>
                    <span style="font-size:12px;padding:4px 10px;border-radius:20px;background:rgba(16,185,129,0.15);color:#10b981">${scenarioLabels[data.scenario] || data.scenario}</span>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">
                    <div><strong>Instruksi:</strong> ${data.instruction}</div>
                    <div><strong>Frame:</strong> ${data.frames_generated}</div>
                    <div><strong>Durasi:</strong> ${data.duration_s}s</div>
                    <div><strong>Sim ID:</strong> ${data.simulation_id}</div>
                </div>
                ${report ? this.renderRiskLevels(report) : ""}
            </div>
        `;
    },

    renderRiskLevels(report) {
        const risks = report.risk_levels || {};
        const riskBadge = (level) => {
            if (level === "referral") return `<span style="background:rgba(239,68,68,0.15);color:#fca5a5;padding:2px 8px;border-radius:12px;font-size:11px">Referal</span>`;
            if (level === "monitor") return `<span style="background:rgba(234,179,8,0.15);color:#fbbf24;padding:2px 8px;border-radius:12px;font-size:11px">Monitor</span>`;
            return `<span style="background:rgba(16,185,129,0.15);color:#10b981;padding:2px 8px;border-radius:12px;font-size:11px">Normal</span>`;
        };
        return `
            <div style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border)">
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
                    <div style="text-align:center;padding:8px;border-radius:8px;background:var(--bg)">
                        <div style="font-size:11px;color:var(--text-secondary)">Stroke</div>
                        <div style="margin-top:4px">${riskBadge(risks.stroke)}</div>
                    </div>
                    <div style="text-align:center;padding:8px;border-radius:8px;background:var(--bg)">
                        <div style="font-size:11px;color:var(--text-secondary)">Parkinson</div>
                        <div style="margin-top:4px">${riskBadge(risks.parkinson)}</div>
                    </div>
                    <div style="text-align:center;padding:8px;border-radius:8px;background:var(--bg)">
                        <div style="font-size:11px;color:var(--text-secondary)">Sarcopenia</div>
                        <div style="margin-top:4px">${riskBadge(risks.sarcopenia)}</div>
                    </div>
                </div>
            </div>
        `;
    },

    renderFullReport(report) {
        if (!report) return "<p>Tidak ada data laporan.</p>";
        const risks = report.risk_levels || {};
        const recommendation = report.recommendation || report.ai_narrative || "";
        const riskBadge = (level) => {
            if (level === "referral") return `<span style="background:#ef4444;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600">REFERAL</span>`;
            if (level === "monitor") return `<span style="background:#eab308;color:#000;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600">MONITOR</span>`;
            return `<span style="background:#10b981;color:#fff;padding:4px 12px;border-radius:20px;font-size:12px;font-weight:600">NORMAL</span>`;
        };

        const metrics = [
            { label: "Mean ASI", value: report.meanASI !== undefined ? report.meanASI.toFixed(3) : "-" },
            { label: "Max ASI", value: report.maxASI !== undefined ? report.maxASI.toFixed(3) : "-" },
            { label: "Sudut Kiri (avg)", value: report.shoulder_angle_L_mean !== undefined ? `${report.shoulder_angle_L_mean.toFixed(1)}°` : "-" },
            { label: "Sudut Kanan (avg)", value: report.shoulder_angle_R_mean !== undefined ? `${report.shoulder_angle_R_mean.toFixed(1)}°` : "-" },
            { label: "Asimetri Sudut", value: report.angle_asymmetry !== undefined ? report.angle_asymmetry.toFixed(1) : "-" },
            { label: "Freq. Dominan", value: report.dominant_freq !== undefined ? `${report.dominant_freq.toFixed(2)} Hz` : "-" },
            { label: "Amplitudo Tremor", value: report.tremor_amplitude !== undefined ? report.tremor_amplitude.toFixed(4) : "-" },
            { label: "Durasi STS", value: report.transition_duration !== undefined ? `${report.transition_duration.toFixed(2)}s` : "-" },
        ];

        return `
            <div style="max-width:700px;margin:0 auto">
                <div style="text-align:center;margin-bottom:24px">
                    <h2 style="margin:0 0 8px 0;font-size:22px">Hasil Assessment Simulasi</h2>
                    <p style="color:var(--text-secondary);font-size:14px">Instruksi: ${report.instruction || "-"}</p>
                </div>
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-bottom:24px">
                    <div style="text-align:center;padding:16px;border-radius:12px;background:var(--card);border:1px solid var(--border)">
                        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">Stroke Risk</div>
                        ${riskBadge(risks.stroke)}
                    </div>
                    <div style="text-align:center;padding:16px;border-radius:12px;background:var(--card);border:1px solid var(--border)">
                        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">Parkinson Risk</div>
                        ${riskBadge(risks.parkinson)}
                    </div>
                    <div style="text-align:center;padding:16px;border-radius:12px;background:var(--card);border:1px solid var(--border)">
                        <div style="font-size:12px;color:var(--text-secondary);margin-bottom:8px">Sarcopenia Risk</div>
                        ${riskBadge(risks.sarcopenia)}
                    </div>
                </div>
                <div style="padding:16px;border-radius:12px;background:var(--card);border:1px solid var(--border);margin-bottom:16px">
                    <h3 style="margin:0 0 12px 0;font-size:15px">Metrik Kinematika</h3>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:13px">
                        ${metrics.map(m => `<div style="padding:6px 0"><span style="color:var(--text-secondary)">${m.label}:</span> <strong>${m.value}</strong></div>`).join("")}
                    </div>
                </div>
                ${recommendation ? `
                <div style="padding:16px;border-radius:12px;background:var(--card);border:1px solid var(--border)">
                    <h3 style="margin:0 0 8px 0;font-size:15px">Rekomendasi</h3>
                    <p style="font-size:13px;line-height:1.6;white-space:pre-wrap">${recommendation}</p>
                </div>
                ` : ""}
            </div>
        `;
    }
};

document.addEventListener("DOMContentLoaded", () => {
    setTimeout(() => SimRunner.init(), 100);
});