"""
WebSocket Handler — Endpoint utama komunikasi real-time.

Fitur baru:
  1. Sequential Assessment: sequential_start → multiple session_start → sequential_end
  2. Alert message: kirim alert saat threshold tercapai
  3. PSD server-side: hitung dan kirim PSD chart data ke client
  4. Confidence score per frame
"""

import json
import time
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.kinematic_engine import KinematicEngine
from core.session_manager import SessionManager
from models.schemas import Landmark

router = APIRouter()
session_mgr = SessionManager()


@router.websocket("/stream")
async def ws_stream(ws: WebSocket):
    """WebSocket endpoint utama streaming landmark dan metrik."""
    await ws.accept()
    engine = None
    session_id = None
    patient_id = ""
    patient_age = None
    is_sequential = False
    sequential_reports = []
    instruction = "raise_hands"

    # ── Sequential Assessment: START ──
    if False:
        pass  # placeholder for sequential block below

    def _send(msg_dict):
        try:
            import asyncio
            asyncio.create_task(ws.send_text(json.dumps(msg_dict)))
        except Exception:
            pass

    try:
        while True:
            raw = await ws.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(ws, "Invalid JSON")
                continue

            msg_type = msg.get("type", "")

            # ══ SEQUENTIAL START (3-in-1) ══
            if msg_type == "sequential_start":
                try:
                    patient_id = msg.get("patient_id", f"PT-{int(time.time())}")
                    patient_age = msg.get("age")
                    if patient_age:
                        try: patient_age = int(patient_age)
                        except: patient_age = None
                    is_sequential = True
                    sequential_reports = []

                    await ws.send_text(json.dumps({
                        "type": "sequential_ack",
                        "status": "ready",
                        "sequence": [
                            {"step": 1, "instruction": "raise_hands",   "label": "Angkat Tangan",   "duration": 15},
                            {"step": 2, "instruction": "stand_still",   "label": "Berdiri Diam",    "duration": 20},
                            {"step": 3, "instruction": "sit_to_stand",  "label": "Duduk ke Berdiri", "duration": 15},
                        ],
                        "server_time": time.time(),
                    }))
                except Exception as e:
                    await _send_error(ws, str(e))

            # ══ SESSION START (bisa normal atau sequential) ══
            elif msg_type == "session_start":
                try:
                    patient_id = msg.get("patient_id", f"PT-{int(time.time())}")
                    instruction = msg.get("instruction", "raise_hands")
                    patient_age = msg.get("age")
                    if patient_age:
                        try: patient_age = int(patient_age)
                        except: patient_age = None

                    session_id = session_mgr.create(patient_id, instruction, age=patient_age)
                    engine = KinematicEngine(instruction=instruction, patient_age=patient_age)

                    await ws.send_text(json.dumps({
                        "type": "ack",
                        "session_id": session_id,
                        "status": "recording",
                        "instruction": instruction,
                        "server_time": time.time(),
                    }))
                except Exception as e:
                    await _send_error(ws, str(e))

            # ══ LANDMARKS ══
            elif msg_type == "landmarks":
                if engine is None:
                    continue

                try:
                    frame = msg.get("frame", 0)
                    timestamp = msg.get("timestamp", time.time())
                    raw_lms = msg.get("landmarks", [])

                    landmarks = []
                    for lm in raw_lms:
                        try:
                            landmarks.append(Landmark(
                                id=int(lm.get("id", 0)),
                                x=float(lm.get("x", 0)),
                                y=float(lm.get("y", 0)),
                                z=float(lm.get("z", 0)),
                                vis=float(lm.get("vis", lm.get("visibility", 0))),
                            ))
                        except (ValueError, TypeError):
                            continue

                    if len(landmarks) < 10:
                        continue

                    metrics = engine.process_frame(frame, timestamp, landmarks)

                    # Tentukan apakah perlu kirim alert
                    alert_type = None
                    if metrics.ASI is not None and metrics.ASI > 0.15:
                        alert_type = "stroke_alert"
                    elif metrics.ASI is not None and metrics.ASI > 0.08:
                        alert_type = "stroke_warning"

                    # Kirim metrik
                    metrics_dict = metrics.model_dump()
                    if alert_type:
                        metrics_dict["alert"] = alert_type
                        # Kirim sebagai message terpisah agar UI bisa flash
                        await ws.send_text(json.dumps({
                            "type": "alert",
                            "alert_type": alert_type,
                            "value": metrics.ASI,
                            "message": "Asimetri terdeteksi!" if alert_type == "stroke_alert" else "Asimetri ringan",
                            "server_time": time.time(),
                        }))

                    await ws.send_text(json.dumps(metrics_dict))

                except Exception as e:
                    print(f"[WS] Frame error: {e}")

            # ══ SESSION END ══
            elif msg_type == "session_end":
                if engine is None:
                    continue

                try:
                    report = engine.finalize(patient_id=patient_id)
                    formatted = session_mgr.save_report(report, session_id)

                    if is_sequential:
                        sequential_reports.append(formatted)
                        await ws.send_text(json.dumps({
                            "type": "step_report",
                            "instruction": instruction,
                            "report": formatted,
                            "step": len(sequential_reports),
                        }))
                        # Reset engine untuk step berikutnya
                        engine = None
                        session_id = None
                    else:
                        await ws.send_text(json.dumps({
                            "type": "report",
                            "report": formatted,
                        }))
                        engine = None
                        session_id = None

                except Exception as e:
                    await _send_error(ws, str(e))

            # ══ SEQUENTIAL END ══
            elif msg_type == "sequential_end":
                if is_sequential and sequential_reports:
                    # Agregasi semua step report
                    aggregated = _aggregate_sequential_reports(sequential_reports, patient_id)
                    await ws.send_text(json.dumps({
                        "type": "sequential_report",
                        "reports": sequential_reports,
                        "aggregated": aggregated,
                    }))
                else:
                    await ws.send_text(json.dumps({
                        "type": "sequential_report",
                        "reports": [],
                        "aggregated": {},
                    }))
                is_sequential = False
                sequential_reports = []

            # ══ HEARTBEAT ══
            elif msg_type == "heartbeat":
                await ws.send_text(json.dumps({
                    "type": "heartbeat",
                    "server_time": time.time(),
                }))

    except WebSocketDisconnect:
        print(f"[WS] Disconnected: session={session_id}")
    except Exception as e:
        print(f"[WS] Error: {e}")


def _aggregate_sequential_reports(reports: list, patient_id: str) -> dict:
    """Aggregasi laporan dari 3 step assessment."""
    import uuid
    from datetime import datetime
    from services.report_generator import ReportGenerator

    stroke_risks = [r.get("risk_levels", {}).get("stroke", "normal") for r in reports]
    park_risks = [r.get("risk_levels", {}).get("parkinson", "normal") for r in reports]
    sarc_risks = [r.get("risk_levels", {}).get("sarcopenia", "normal") for r in reports]

    def worst(risk_list):
        if "referal" in risk_list: return "referal"
        if "monitor" in risk_list: return "monitor"
        return "normal"

    # Confidence score overall (0-100)
    confidences = [r.get("confidence_scores", {}) for r in reports]
    stroke_c = max([c.get("stroke", 0) for c in confidences], default=0)
    park_c = max([c.get("parkinson", 0) for c in confidences], default=0)
    sarc_c = max([c.get("sarcopenia", 0) for c in confidences], default=0)
    overall_conf = (stroke_c + park_c + sarc_c) / 3 * 100

    timestamp = datetime.now().isoformat()

    recommendation = ""
    if worst(stroke_risks) == "referal":
        recommendation = "REKOMENDASI: Rujukan neurologist — indikasi stroke ringan / TIA."
    elif worst(park_risks) == "referal":
        recommendation = "REKOMENDASI: Rujukan neurologist — indikasi tremor patologis (Parkinson)."
    elif worst(sarc_risks) == "referal":
        recommendation = "REKOMENDASI: Rujukan geriatri — indikasi sarcopenia (penurunan massa otot)."
    elif worst(stroke_risks) == "monitor" or worst(park_risks) == "monitor" or worst(sarc_risks) == "monitor":
        recommendation = "REKOMENDASI: Monitoring lanjutan — beberapa parameter di batas atas normal."
    else:
        recommendation = "REKOMENDASI: Normal — tidak terdeteksi indikasi anomali signifikan."

    return {
        "report_id": str(uuid.uuid4()),
        "patient_id": patient_id,
        "timestamp": timestamp,
        "instruction": "sequential_3in1",
        "risk_levels": {
            "stroke": worst(stroke_risks),
            "parkinson": worst(park_risks),
            "sarcopenia": worst(sarc_risks),
        },
        "confidence_scores": {
            "stroke": round(stroke_c, 3),
            "parkinson": round(park_c, 3),
            "sarcopenia": round(sarc_c, 3),
            "overall": round(overall_conf, 1),
        },
        "recommendation": recommendation,
        "narrative": f"Laporan Skrining 3-in-1.\n\n" + "\n".join([
            f"Step {i+1} ({r.get('instruction','')}) — Risiko: {r.get('risk_levels',{}).get('stroke', 'normal')}"
            for i, r in enumerate(reports)
        ]),
        "step_count": len(reports),
    }


async def _send_error(ws: WebSocket, message: str):
    try:
        await ws.send_text(json.dumps({"type": "error", "message": message}))
    except Exception:
        pass