/**
 * SkeletonRenderer — Menggambar kerangka pose + angle annotations di canvas.
 *
 * Perbaikan:
 *   1. Robust landmark format handling (support both {id} indexed and array-indexed)
 *   2. Smooth angle interpolation untuk mengurangi jittering
 *   3. Better bone visibility with gradient colors
 *   4. Joint confidence visualization
 */

class SkeletonRenderer {
    constructor(videoEl, canvasEl) {
        this.video = videoEl;
        this.canvas = canvasEl;
        this.ctx = canvasEl.getContext("2d");

        this.BONES = [
            { from: 11, to: 12, name: "shoulders" },
            { from: 11, to: 13 }, { from: 13, to: 15, name: "elbow_L" },
            { from: 12, to: 14 }, { from: 14, to: 16, name: "elbow_R" },
            { from: 11, to: 23 }, { from: 12, to: 24 },
            { from: 23, to: 24, name: "hips" },
            { from: 23, to: 25 }, { from: 25, to: 27 },
            { from: 24, to: 26 }, { from: 26, to: 28 },
            // Tambahan: wrist connections
            { from: 15, to: 17 }, { from: 16, to: 18 },
        ];

        // Colors
        this.COLOR_GOOD = "#10b981";
        this.COLOR_WARN = "rgba(245,158,11,0.7)";
        this.COLOR_ANGLE_L = "#0ea5e9";
        this.COLOR_ANGLE_R = "#8b5cf6";

        // Smooth angle interpolation
        this._prevAngles = {};
        this._smoothFactor = 0.3; // Lower = smoother

        this.resize();
        window.addEventListener("resize", () => this.resize());
    }

    resize() {
        const w = this.video.videoWidth || 640;
        const h = this.video.videoHeight || 480;
        if (this.canvas.width !== w || this.canvas.height !== h) {
            this.canvas.width = w;
            this.canvas.height = h;
        }
    }

    /**
     * Draw skeleton dari landmarks.
     * Supports two formats:
     *   1. Array of {id, x, y, z, vis} (from app conversion)
     *   2. Raw MediaPipe poseLandmarks array (index = id)
     */
    draw(landmarks, angleData = null) {
        this.resize(); // Ensure canvas matches video

        const w = this.canvas.width;
        const h = this.canvas.height;
        this.ctx.clearRect(0, 0, w, h);

        if (!landmarks || landmarks.length === 0) return;

        // Build lookup: normalize to {id: {x, y, vis}} format
        const pts = {};
        landmarks.forEach((lm, index) => {
            const id = (lm.id !== undefined && lm.id !== null) ? lm.id : index;
            const vis = lm.vis !== undefined ? lm.vis : (lm.visibility !== undefined ? lm.visibility : 0);
            pts[id] = {
                x: lm.x * w,
                y: lm.y * h,
                vis: vis,
            };
        });

        // ── Draw bones ──
        this.ctx.lineCap = "round";
        this.ctx.lineJoin = "round";

        this.BONES.forEach(bone => {
            const a = pts[bone.from];
            const b = pts[bone.to];
            if (!a || !b) return;

            const confidence = Math.min(a.vis, b.vis);
            const isGood = confidence > 0.6;

            // Glow effect for good confidence
            if (isGood) {
                this.ctx.shadowColor = "rgba(34,197,94,0.3)";
                this.ctx.shadowBlur = 5;
            }

            this.ctx.strokeStyle = isGood ? this.COLOR_GOOD : this.COLOR_WARN;
            this.ctx.lineWidth = isGood ? 3 : 2;
            this.ctx.globalAlpha = Math.max(0.3, confidence);

            this.ctx.beginPath();
            this.ctx.moveTo(a.x, a.y);
            this.ctx.lineTo(b.x, b.y);
            this.ctx.stroke();

            this.ctx.shadowBlur = 0;
            this.ctx.globalAlpha = 1.0;
        });

        // ── Draw joints ──
        for (const [id, p] of Object.entries(pts)) {
            if (p.vis > 0.5) {
                // Outer glow
                this.ctx.fillStyle = p.vis > 0.7
                    ? this.COLOR_GOOD
                    : this.COLOR_WARN;
                this.ctx.globalAlpha = Math.max(0.4, p.vis);
                this.ctx.beginPath();
                this.ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
                this.ctx.fill();

                // Inner dot (white core)
                this.ctx.fillStyle = "rgba(255,255,255,0.8)";
                this.ctx.beginPath();
                this.ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
                this.ctx.fill();

                this.ctx.globalAlpha = 1.0;
            }
        }

        // ── Draw angle annotations with smooth interpolation ──
        if (angleData) {
            this._drawAngleSmooth(pts, 11, "L", angleData.shoulder_angle_L, this.COLOR_ANGLE_L);
            this._drawAngleSmooth(pts, 12, "R", angleData.shoulder_angle_R, this.COLOR_ANGLE_R);
        }
    }

    _drawAngleSmooth(pts, jointId, side, rawAngle, color) {
        if (!pts[jointId] || rawAngle === null || rawAngle === undefined) return;

        // Smooth interpolation to reduce jitter
        const key = `${jointId}_${side}`;
        if (this._prevAngles[key] !== undefined) {
            rawAngle = this._prevAngles[key] + (rawAngle - this._prevAngles[key]) * this._smoothFactor;
        }
        this._prevAngles[key] = rawAngle;

        const p = pts[jointId];

        // Background pill
        const text = `${rawAngle.toFixed(1)}°`;
        this.ctx.font = "bold 11px Inter, sans-serif";
        const textWidth = this.ctx.measureText(text).width;
        const offsetX = side === "L" ? -textWidth - 16 : 10;
        const offsetY = -22;

        // Pill background
        this.ctx.fillStyle = "rgba(0,0,0,0.6)";
        const pillX = p.x + offsetX - 4;
        const pillY = p.y + offsetY - 10;
        const pillW = textWidth + 8;
        const pillH = 16;
        this.ctx.beginPath();
        this.ctx.roundRect(pillX, pillY, pillW, pillH, 4);
        this.ctx.fill();

        // Text
        this.ctx.fillStyle = color;
        this.ctx.textAlign = "left";
        this.ctx.fillText(text, p.x + offsetX, p.y + offsetY);
    }

    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this._prevAngles = {};
    }
}
