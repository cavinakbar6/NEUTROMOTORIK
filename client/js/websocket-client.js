/**
 * WSClient — WebSocket connection manager with auto-reconnect.
 *
 * Perbaikan:
 *   1. Dynamic URL menggunakan window.location.host
 *   2. Support untuk age parameter di session_start
 *   3. Better reconnection with jitter
 */

class WSClient {
    constructor(url) {
        // Hardcode port 8765 karena backend Python berjalan di port ini (terpisah dari web server Vite/Live Server)
        this.url = url || `ws://127.0.0.1:8765/ws/stream`;

        this.ws = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnect = 20;
        this.pingTimer = null;
        this.lastPing = 0;
        this.latency = 0;
        this.onMetrics = null;
        this.onReport = null;
        this.onAck = null;
        this.onError = null;
        this.onStatusChange = null;
    }

    connect() {
        try {
            this.ws = new WebSocket(this.url);
        } catch (e) {
            console.error("[WS] Failed:", e);
            this._scheduleReconnect();
            return;
        }

        this.ws.onopen = () => {
            this.connected = true;
            this.reconnectAttempts = 0;
            this._startHeartbeat();
            console.log("[WS] Connected to", this.url);
            if (this.onStatusChange) this.onStatusChange("connected");
        };

        this.ws.onmessage = (e) => {
            try { this._route(JSON.parse(e.data)); }
            catch (err) { console.error("[WS] Parse error:", err); }
        };

        this.ws.onclose = (e) => {
            this.connected = false;
            this._stopHeartbeat();
            if (this.onStatusChange) this.onStatusChange("disconnected");
            this._scheduleReconnect();
        };

        this.ws.onerror = () => {};
    }

    _route(data) {
        switch (data.type) {
            case "metrics":           if (this.onMetrics) this.onMetrics(data); break;
            case "report":            if (this.onReport)  this.onReport(data.report); break;
            case "step_report":       if (this.onReport)  this.onReport(data.report); break;
            case "sequential_report": if (this.onReport)  this.onReport(data.aggregated); break;
            case "sequential_ack":    console.log("[WS] Sequential:", data); break;
            case "ack":               if (this.onAck)     this.onAck(data); break;
            case "alert":
                console.warn("[WS] Alert:", data.alert_type, data.message);
                if (this.onMetrics) this.onMetrics(data); // pass alert through metrics handler
                break;
            case "heartbeat":
                this.latency = Math.round(performance.now() - this.lastPing);
                break;
            case "error":
                console.warn("[WS] Server error:", data.message);
                if (this.onError) this.onError(data.message);
                break;
        }
    }

    send(obj) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(obj));
        }
    }

    sendLandmarks(frame, timestamp, landmarks) {
        this.send({ type: "landmarks", frame, timestamp, landmarks });
    }

    startSession(patientId, instruction, age) {
        const msg = {
            type: "session_start",
            patient_id: patientId,
            instruction: instruction,
        };
        // Include age if provided (for age-stratified sarcopenia thresholds)
        if (age != null && age !== "" && !isNaN(parseInt(age))) {
            msg.age = parseInt(age);
        }
        this.send(msg);
    }

    startSequential(patientId, age) {
        const msg = {
            type: "sequential_start",
            patient_id: patientId,
        };
        if (age != null && age !== "" && !isNaN(parseInt(age))) {
            msg.age = parseInt(age);
        }
        this.send(msg);
    }

    endSession(sessionId) {
        this.send({ type: "session_end", session_id: sessionId });
    }

    getLatency() { return this.latency; }

    _startHeartbeat() {
        this.pingTimer = setInterval(() => {
            this.lastPing = performance.now();
            this.send({ type: "heartbeat" });
        }, 3000);
    }

    _stopHeartbeat() {
        clearInterval(this.pingTimer);
    }

    _scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnect) return;
        this.reconnectAttempts++;
        // Exponential backoff with jitter
        const base = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts), 20000);
        const jitter = Math.random() * 500;
        const delay = base + jitter;
        console.log(`[WS] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
    }
}
