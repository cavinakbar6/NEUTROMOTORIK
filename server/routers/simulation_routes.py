"""
Simulation routes — REST API for running simulated assessments.
"""

import json
import time
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from core.simulation import SimulationEngine, SimulationConfig
from core.kinematic_engine import KinematicEngine
from core.session_manager import SessionManager
from models.database import Database
from models.schemas import Landmark, InstructionType

router = APIRouter()
db = Database()
session_mgr = SessionManager()


class SimStartRequest(BaseModel):
    instruction: str = Field(default="raise_hands", description="Assessment instruction type")
    fps: int = Field(default=30, description="Frames per second")
    duration_s: float = Field(default=15.0, description="Duration in seconds")
    patient_age: int = Field(default=65, description="Patient age for age-stratified thresholds")
    scenario: str = Field(default="normal", description="Simulation scenario preset")
    noise_level: float = Field(default=0.002, description="Landmark noise standard deviation")
    patient_id: Optional[str] = Field(default=None, description="Patient ID (auto-generated if omitted")


@router.post("/start")
async def start_simulation(req: SimStartRequest):
    """Start a simulation. Processes all frames through KinematicEngine and returns a clinical report."""
    valid_instructions = [e.value for e in InstructionType]
    if req.instruction not in valid_instructions:
        raise HTTPException(400, detail=f"Invalid instruction. Must be one of: {valid_instructions}")

    valid_scenarios = ("normal", "stroke_mild", "stroke_severe", "parkinson_tremor", "sarcopenia_slow")
    if req.scenario not in valid_scenarios:
        raise HTTPException(400, detail=f"Invalid scenario. Must be one of: {valid_scenarios}")

    config = SimulationConfig(
        instruction=req.instruction,
        fps=req.fps,
        duration_s=req.duration_s,
        patient_age=req.patient_age,
        scenario=req.scenario,
        noise_level=req.noise_level,
    )

    engine_sim = SimulationEngine(config)
    engine_kin = KinematicEngine(instruction=req.instruction, fps=req.fps, patient_age=req.patient_age)

    patient_id = req.patient_id or f"SIM-{int(time.time())}"
    session_id = session_mgr.create(patient_id, req.instruction, age=req.patient_age)

    # Generate and process all frames
    all_frames_data = []
    while True:
        result = engine_sim.generate_frame()
        if result is None:
            break

        frame_num, timestamp, landmarks = result
        frame_dict = {
            "frame_number": frame_num,
            "timestamp": timestamp,
            "landmarks_json": json.dumps([lm.model_dump() for lm in landmarks]),
        }
        all_frames_data.append(frame_dict)

        # Process through kinematic engine
        if engine_kin._is_rehab:
            engine_kin.process_rehab_frame(frame_num, timestamp, landmarks)
        else:
            engine_kin.process_frame(frame_num, timestamp, landmarks)

    # Finalize the report
    report = engine_kin.finalize(patient_id=patient_id)
    formatted_report = session_mgr.save_report(report, session_id)

    # Save landmarks for replay
    if all_frames_data:
        db.save_landmarks_batch(session_id, all_frames_data)

    return {
        "simulation_id": session_id,
        "patient_id": patient_id,
        "instruction": req.instruction,
        "scenario": req.scenario,
        "duration_s": req.duration_s,
        "fps": req.fps,
        "frames_generated": len(all_frames_data),
        "report": formatted_report,
    }


@router.get("/{simulation_id}/replay")
async def get_simulation_replay(simulation_id: str):
    """Get landmark data from a simulation for replay."""
    from models.replay import LandmarkFrame, ReplayData

    session = db.fetchone("SELECT id FROM sessions WHERE id=?", (simulation_id,))
    if not session:
        raise HTTPException(404, detail="Simulation not found")

    rows = db.get_landmarks(simulation_id)
    if not rows:
        raise HTTPException(404, detail="No replay data found for this simulation")

    frames = []
    for frame_number, timestamp, landmarks_json in rows:
        frames.append(LandmarkFrame(
            frame_number=frame_number,
            timestamp=timestamp,
            landmarks_json=landmarks_json,
        ))

    duration = frames[-1].timestamp - frames[0].timestamp if len(frames) > 1 else 0.0
    return ReplayData(
        session_id=simulation_id,
        frames=frames,
        total_frames=len(frames),
        duration_s=round(duration, 2),
    ).model_dump()