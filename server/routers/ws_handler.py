"""
WebSocket Handler — Endpoint utama komunikasi real-time.

Perbaikan:
  1. Gunakan ReportGenerator.to_dict() untuk format report → client
  2. SessionManager.save_report() sekarang return formatted dict
  3. Pass patient age untuk age-stratified sarcopenia thresholds
  4. Robust error handling per-frame (no crash on single bad frame)

Protocol:
    1. Client → session_start {patient_id, instruction, age?}
    2. Client → landmarks (repeated per frame)
    3. Server → metrics (per frame, includes PSD periodically)
    4. Client → session_end
    5. Server → report (formatted via ReportGenerator)
"""

import json
import time
import traceback
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.kinematic_engine import KinematicEngine
from core.session_manager import SessionManager
from models.schemas import (
    SessionStartMsg, LandmarksMsg, HeartbeatMsg, Landmark
)

router = APIRouter()
session_mgr = SessionManager()


@router.websocket("/stream")
async def ws_stream(ws: WebSocket):
    """WebSocket endpoint utama untuk streaming landmark dan metrik."""
    await ws.accept()
    engine = None
    session_id = None
    patient_id = ""
    patient_age = None

    try:
        while True:
            raw = await ws.receive_text()

            # Parse JSON
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(ws, "Invalid JSON")
                continue

            msg_type = msg.get("type", "")

            # ── SESSION START ──
            if msg_type == "session_start":
                try:
                    patient_id = msg.get("patient_id", f"PT-{int(time.time())}")
                    instruction = msg.get("instruction", "raise_hands")
                    patient_age = msg.get("age", None)

                    # Convert age to int if provided
                    if patient_age is not None:
                        try:
                            patient_age = int(patient_age)
                        except (ValueError, TypeError):
                            patient_age = None

                    session_id = session_mgr.create(
                        patient_id, instruction, age=patient_age
                    )
                    engine = KinematicEngine(
                        instruction=instruction,
                        patient_age=patient_age,
                    )

                    await ws.send_text(json.dumps({
                        "type": "ack",
                        "session_id": session_id,
                        "status": "recording",
                        "server_time": time.time(),
                    }))

                except Exception as e:
                    print(f"[WS] session_start error: {e}")
                    traceback.print_exc()
                    await _send_error(ws, f"Invalid session_start: {e}")

            # ── LANDMARKS ──
            elif msg_type == "landmarks":
                if engine is None:
                    await _send_error(ws, "No active session. Send session_start first.")
                    continue

                try:
                    # Parse landmarks manually for robustness
                    frame = msg.get("frame", 0)
                    timestamp = msg.get("timestamp", time.time())
                    raw_landmarks = msg.get("landmarks", [])

                    landmarks = []
                    for lm in raw_landmarks:
                        try:
                            landmarks.append(Landmark(
                                id=int(lm.get("id", 0)),
                                x=float(lm.get("x", 0)),
                                y=float(lm.get("y", 0)),
                                z=float(lm.get("z", 0)),
                                vis=float(lm.get("vis", lm.get("visibility", 0))),
                            ))
                        except (ValueError, TypeError):
                            continue  # Skip malformed landmark

                    if len(landmarks) < 10:
                        continue  # Not enough landmarks

                    metrics = engine.process_frame(
                        frame_id=frame,
                        timestamp=timestamp,
                        landmarks=landmarks,
                    )
                    await ws.send_text(metrics.model_dump_json())

                except Exception as e:
                    # Don't crash the whole session on a single bad frame
                    print(f"[WS] Frame processing error: {e}")
                    traceback.print_exc()

            # ── SESSION END ──
            elif msg_type == "session_end":
                if engine is None:
                    await _send_error(ws, "No active session to end.")
                    continue

                try:
                    report = engine.finalize(patient_id=patient_id)
                    # save_report now returns formatted dict via ReportGenerator
                    formatted_report = session_mgr.save_report(report, session_id)

                    await ws.send_text(json.dumps({
                        "type": "report",
                        "report": formatted_report,
                    }))

                    # Reset
                    engine = None
                    session_id = None

                except Exception as e:
                    print(f"[WS] Finalize error: {e}")
                    traceback.print_exc()
                    await _send_error(ws, f"Finalize error: {e}")

            # ── HEARTBEAT ──
            elif msg_type == "heartbeat":
                await ws.send_text(json.dumps({
                    "type": "heartbeat",
                    "server_time": time.time(),
                }))

    except WebSocketDisconnect:
        print(f"[WS] Client disconnected: session={session_id}")
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        traceback.print_exc()


async def _send_error(ws: WebSocket, message: str):
    """Kirim pesan error ke client."""
    try:
        await ws.send_text(json.dumps({"type": "error", "message": message}))
    except Exception:
        pass
