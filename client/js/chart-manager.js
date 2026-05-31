/**
 * ChartManager — Live ASI Time Series + PSD charts with dark clinical theme.
 * Uses Chart.js with minimal animation for real-time performance.
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
                        borderColor: "#0d9488",
                        backgroundColor: "rgba(13, 148, 136, 0.08)",
                        fill: true,
                        tension: 0.4,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                    {
                        label: "Normal (0.08)",
                        data: [],
                        borderColor: "rgba(34, 197, 94, 0.5)",
                        borderDash: [4, 4],
                        pointRadius: 0,
                        borderWidth: 1,
                    },
                    {
                        label: "Referral (0.15)",
                        data: [],
                        borderColor: "rgba(220, 38, 38, 0.5)",
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
                        borderColor: "#7c3aed",
                        backgroundColor: "rgba(124, 58, 237, 0.06)",
                        fill: true,
                        tension: 0.3,
                        pointRadius: 0,
                        borderWidth: 2,
                    },
                    {
                        label: "Zona Parkinson",
                        data: [],
                        borderColor: "rgba(220, 38, 38, 0.25)",
                        backgroundColor: "rgba(220, 38, 38, 0.03)",
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
                        ticks: { color: "#64748b", font: { size: 10 } },
                        grid: { color: "rgba(148, 163, 184, 0.15)" },
                        title: { display: true, text: "Power", color: "#64748b", font: { size: 10 } },
                    },
                    x: {
                        ticks: { color: "#64748b", font: { size: 10 }, maxTicksLimit: 10 },
                        grid: { color: "rgba(148, 163, 184, 0.15)" },
                        title: { display: true, text: "Frequency (Hz)", color: "#64748b", font: { size: 10 } },
                    },
                },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#64748b", boxWidth: 8, padding: 8, font: { size: 10 } },
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
                    ticks: { color: "#64748b", font: { size: 10 } },
                        grid: { color: "rgba(148, 163, 184, 0.15)" },
                        title: { display: true, text: yLabel, color: "#64748b", font: { size: 10 } },
                },
                    x: {
                    display: false,
                    grid: { color: "rgba(148, 163, 184, 0.15)" },
                },
            },
                plugins: {
                    legend: {
                        position: "bottom",
                        labels: { color: "#64748b", boxWidth: 8, padding: 8, font: { size: 10 } },
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
        this.asiChart.data.datasets[1].data = this.frameLabels.map(() => 0.08);
        this.asiChart.data.datasets[2].data = this.frameLabels.map(() => 0.15);
        this.asiChart.update("none");
    }

    updatePSD(freqs, power) {
        if (!this.psdChart || !freqs || !power || freqs.length === 0) return;

        const labels = freqs.map(f => typeof f === "number" ? f.toFixed(1) : f);

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