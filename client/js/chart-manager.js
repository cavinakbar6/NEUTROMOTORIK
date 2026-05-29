/**
 * ChartManager — Grafik live ASI Time Series + PSD (Power Spectral Density).
 * Menggunakan Chart.js dengan animasi minimal untuk real-time performance.
 *
 * Perbaikan:
 *   1. updatePSD() sekarang dipanggil dari handleMetrics()
 *   2. PSD chart terisi dengan data dari server
 *   3. Better axis scaling
 *   4. Tremor zone highlighting pada PSD chart
 */

class ChartManager {
    constructor() {
        this.asiChart = null;
        this.psdChart = null;
        this.asiData = [];
        this.frameLabels = [];
        this.maxPoints = 300;
    }

    initASI() {
        const ctx = document.getElementById("chart-asi");
        if (!ctx) return;
        if (this.asiChart) this.asiChart.destroy();

        this.asiChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "ASI",
                        data: [],
                        borderColor: "#10b981",
                        backgroundColor: "rgba(16, 185, 129, 0.08)",
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                    {
                        label: "Normal (0.08)",
                        data: [],
                        borderColor: "rgba(34,197,94,0.5)",
                        borderDash: [4, 4],
                        pointRadius: 0,
                        borderWidth: 1,
                    },
                    {
                        label: "Referal (0.15)",
                        data: [],
                        borderColor: "rgba(239,68,68,0.5)",
                        borderDash: [4, 4],
                        pointRadius: 0,
                        borderWidth: 1,
                    },
                ],
            },
            options: this._lineOptions(0, 0.4, "ASI"),
        });
    }

    initPSD() {
        const ctx = document.getElementById("chart-psd");
        if (!ctx) return;
        if (this.psdChart) this.psdChart.destroy();

        this.psdChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: [],
                datasets: [
                    {
                        label: "Power",
                        data: [],
                        borderColor: "#8b5cf6",
                        backgroundColor: "rgba(139,92,246,0.1)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                    {
                        // Parkinsonian tremor zone highlight (3.5-7 Hz)
                        label: "Zona Parkinson",
                        data: [],
                        borderColor: "rgba(239,68,68,0.3)",
                        backgroundColor: "rgba(239,68,68,0.05)",
                        fill: true,
                        tension: 0,
                        pointRadius: 0,
                        borderWidth: 1,
                        borderDash: [2, 2],
                    },
                ],
            },
            options: {
                responsive: true,
                animation: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: "#5a6577", font: { size: 10 } },
                        grid: { color: "rgba(16,185,129,0.1)" },
                        title: { display: true, text: "Power", color: "#5a6577", font: { size: 10 } },
                    },
                    x: {
                        ticks: { color: "#5a6577", font: { size: 10 }, maxTicksLimit: 10 },
                        grid: { color: "rgba(16,185,129,0.1)" },
                        title: { display: true, text: "Frequency (Hz)", color: "#5a6577", font: { size: 10 } },
                    },
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#5a6577", boxWidth: 8, padding: 8, font: { size: 10 } },
                    },
                },
            },
        });
    }

    _lineOptions(yMin, yMax, yLabel) {
        return {
            responsive: true,
            animation: false,
            interaction: { intersect: false, mode: "index" },
            scales: {
                y: {
                    min: yMin,
                    max: yMax,
                    ticks: { color: "#5a6577", font: { size: 10 } },
                    grid: { color: "rgba(16,185,129,0.1)" },
                    title: { display: true, text: yLabel, color: "#5a6577", font: { size: 10 } },
                },
                x: {
                    display: false,
                    grid: { color: "rgba(16,185,129,0.1)" },
                },
            },
            plugins: {
                legend: {
                    position: "bottom",
                    labels: { color: "#5a6577", boxWidth: 8, padding: 8, font: { size: 10 } },
                },
            },
        };
    }

    updateASI(frame, value) {
        this.frameLabels.push(frame);
        this.asiData.push(value);
        if (this.frameLabels.length > this.maxPoints) {
            this.frameLabels.shift();
            this.asiData.shift();
        }
        if (!this.asiChart) return;
        this.asiChart.data.labels = [...this.frameLabels];
        this.asiChart.data.datasets[0].data = [...this.asiData];
        // Updated threshold lines to match clinical_thresholds.py
        this.asiChart.data.datasets[1].data = this.frameLabels.map(() => 0.08);
        this.asiChart.data.datasets[2].data = this.frameLabels.map(() => 0.15);
        this.asiChart.update("none");
    }

    updatePSD(freqs, power) {
        if (!this.psdChart || !freqs || !power || freqs.length === 0) return;

        const labels = freqs.map(f => typeof f === "number" ? f.toFixed(1) : f);

        // Generate Parkinson zone overlay (3.5–7.0 Hz)
        const maxPower = Math.max(...power, 0.001);
        const parkZone = freqs.map(f => {
            return (f >= 3.5 && f <= 7.0) ? maxPower * 0.3 : 0;
        });

        this.psdChart.data.labels = labels;
        this.psdChart.data.datasets[0].data = [...power];
        this.psdChart.data.datasets[1].data = parkZone;
        this.psdChart.update("none");
    }

    destroy() {
        if (this.asiChart) { this.asiChart.destroy(); this.asiChart = null; }
        if (this.psdChart) { this.psdChart.destroy(); this.psdChart = null; }
        this.asiData = [];
        this.frameLabels = [];
    }
}
