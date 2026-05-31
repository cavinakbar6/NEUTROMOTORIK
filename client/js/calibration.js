/**
 * Calibration Module — Camera distance normalization.
 *
 * Monitors shoulder width from incoming landmarks to estimate
 * camera distance and compute a scale factor for normalizing
 * measurements across different distances.
 */

class Calibrator {
    constructor() {
        this.shoulderWidths = [];
        this.calibrated = false;
        this.FRAMES_NEEDED = 30;
        this.REF_WIDTH_M = 0.40;
        this.MIN_VISIBILITY = 0.6;
        this.result = null;
        this._uiContainer = null;
    }

    update(landmarks) {
        if (this.calibrated) return this.result;

        const lSh = landmarks.find(l => l.id === 11);
        const rSh = landmarks.find(l => l.id === 12);

        if (!lSh || !rSh) return null;
        if ((lSh.visibility || lSh.vis || 0) < this.MIN_VISIBILITY) return null;
        if ((rSh.visibility || rSh.vis || 0) < this.MIN_VISIBILITY) return null;

        const dx = rSh.x - lSh.x;
        const dy = rSh.y - lSh.y;
        const width = Math.sqrt(dx * dx + dy * dy);

        if (width < 0.001) return null;

        this.shoulderWidths.push(width);
        this._updateProgress();

        if (this.shoulderWidths.length < this.FRAMES_NEEDED) return null;

        // Compute median for robustness
        const sorted = [...this.shoulderWidths].sort((a, b) => a - b);
        const median = sorted[Math.floor(sorted.length / 2)];

        const distance = this.REF_WIDTH_M / median;
        const scaleFactor = median / this.REF_WIDTH_M;

        // Confidence: low coefficient of variation = high confidence
        const mean = this.shoulderWidths.reduce((a, b) => a + b, 0) / this.shoulderWidths.length;
        const std = Math.sqrt(this.shoulderWidths.reduce((a, b) => a + (b - mean) ** 2, 0) / this.shoulderWidths.length);
        const cv = mean > 0 ? std / mean : 1.0;
        const confidence = Math.max(0, Math.min(1, 1 - cv));

        this.result = {
            scaleFactor,
            distanceM: Math.round(distance * 100) / 100,
            shoulderWidthPx: Math.round(median * 100000) / 100000,
            confidence: Math.round(confidence * 100) / 100,
            calibrated: true,
        };
        this.calibrated = true;
        this._showResult();
        return this.result;
    }

    getDistanceEstimate() {
        return this.result ? this.result.distanceM : null;
    }

    getScaleFactor() {
        return this.result ? this.result.scaleFactor : null;
    }

    reset() {
        this.shoulderWidths = [];
        this.calibrated = false;
        this.result = null;
        this._removeUI();
    }

    _updateProgress() {
        const el = this._getOrCreateContainer();
        const progress = Math.min(100, Math.round((this.shoulderWidths.length / this.FRAMES_NEEDED) * 100));
        const bar = el.querySelector('.calib-progress-bar');
        const text = el.querySelector('.calib-text');
        if (bar) bar.style.width = progress + '%';
        if (text) text.textContent = `Calibrating: ${this.shoulderWidths.length}/${this.FRAMES_NEEDED} frames`;
    }

    _showResult() {
        const el = this._getOrCreateContainer();
        const dist = this.result.distanceM;
        let warning = '';
        if (dist > 2.0) {
            warning = '<span style="color:#ff9800;">⚠ Too far — move closer (~1.3m ideal)</span>';
        } else if (dist < 0.5) {
            warning = '<span style="color:#ff9800;">⚠ Too close — move back (~1.3m ideal)</span>';
        } else {
            warning = '<span style="color:#4caf50;">✓ Good distance</span>';
        }
        el.innerHTML = `
            <div style="font-size:12px;color:#aaa;margin-bottom:2px;">Camera Distance</div>
            <div style="font-size:16px;font-weight:bold;color:#fff;">${dist}m</div>
            <div style="font-size:11px;margin-top:2px;">${warning}</div>
            <div style="font-size:10px;color:#666;margin-top:2px;">Confidence: ${Math.round(this.result.confidence * 100)}%</div>
        `;
    }

    _getOrCreateContainer() {
        if (this._uiContainer && document.contains(this._uiContainer)) return this._uiContainer;
        let el = document.getElementById('calibration-indicator');
        if (!el) {
            el = document.createElement('div');
            el.id = 'calibration-indicator';
            el.style.cssText = 'position:fixed;top:60px;right:16px;background:#1a1a2e;border:1px solid #333;border-radius:8px;padding:8px 14px;z-index:1000;min-width:160px;text-align:center;font-family:monospace;';
            const barWrap = document.createElement('div');
            barWrap.style.cssText = 'width:100%;height:4px;background:#333;border-radius:2px;margin-top:4px;overflow:hidden;';
            const bar = document.createElement('div');
            bar.className = 'calib-progress-bar';
            bar.style.cssText = 'height:100%;background:#4caf50;width:0%;transition:width 0.2s;';
            barWrap.appendChild(bar);
            const text = document.createElement('div');
            text.className = 'calib-text';
            text.style.cssText = 'font-size:11px;color:#aaa;margin-top:4px;';
            text.textContent = 'Calibrating: 0/' + this.FRAMES_NEEDED + ' frames';
            el.appendChild(text);
            el.appendChild(barWrap);
            document.body.appendChild(el);
        }
        this._uiContainer = el;
        return el;
    }

    _removeUI() {
        const el = document.getElementById('calibration-indicator');
        if (el) el.remove();
    }
}

// Export for use in main.js
window.Calibrator = Calibrator;