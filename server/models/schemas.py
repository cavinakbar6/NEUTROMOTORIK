"""
Pydantic Schemas — Data models untuk WebSocket communication dan REST API.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


# ─── Enums ──────────────────────────────────────────────

class RiskLevel(str, Enum):
    NORMAL  = "normal"
    MONITOR = "monitor"
    REFERAL = "referal"


class InstructionType(str, Enum):
    RAISE_HANDS   = "raise_hands"
    STAND_STILL   = "stand_still"
    SIT_TO_STAND  = "sit_to_stand"
    REHAB_ARM_RAISE = "rehab_arm_raise"
    REHAB_SQUAT     = "rehab_squat"


# ─── Landmark ───────────────────────────────────────────

class Landmark(BaseModel):
    """Satu titik landmark MediaPipe 3D."""
    id:  int   = Field(..., description="Indeks landmark MediaPipe (0-32)")
    x:   float = Field(..., description="Koordinat X normalisasi")
    y:   float = Field(..., description="Koordinat Y normalisasi")
    z:   float = Field(..., description="Kedalaman relatif")
    vis: float = Field(0.0, ge=0.0, le=1.0, description="Skor visibility [0-1]")


# ─── WebSocket Messages ─────────────────────────────────

class SessionStartMsg(BaseModel):
    type:        str = "session_start"
    patient_id:  str
    instruction: InstructionType
    metadata:    Optional[dict] = None


class LandmarksMsg(BaseModel):
    type:      str = "landmarks"
    frame:     int
    timestamp: float
    landmarks: List[Landmark]


class SessionEndMsg(BaseModel):
    type:       str = "session_end"
    session_id: str


class HeartbeatMsg(BaseModel):
    type: str = "heartbeat"


# ─── Server → Client Messages ───────────────────────────

class AckMsg(BaseModel):
    type:       str = "ack"
    session_id: str
    status:     str = "recording"
    server_time: float


class KinematicMetrics(BaseModel):
    """Metrik kinematika per frame — dikirim server ke client."""
    type:               str = "metrics"
    frame:              int
    shoulder_angle_L:   Optional[float] = None
    shoulder_angle_R:   Optional[float] = None
    elbow_angle_L:      Optional[float] = None
    elbow_angle_R:      Optional[float] = None
    ASI:                Optional[float] = None
    dominant_freq_hz:   Optional[float] = None
    tremor_amplitude:   Optional[float] = None
    sts_phase:          Optional[str]  = None
    sts_duration:       Optional[float] = None
    psd_freqs:          Optional[List[float]] = None
    psd_power:          Optional[List[float]] = None
    confidence:         Optional[float] = None
    status:             str = "recording"


class RehabMetrics(BaseModel):
    """Metrik gamifikasi rehab per frame — dikirim ke client PhysioLens."""
    type:          str = "rehab_metrics"
    frame:         int
    rep_count:     int   = 0
    form_score:    float = 0.0
    feedback_msg:  str   = ""
    phase:         Optional[str] = None
    target_reps:   int   = 10


class HeartbeatAck(BaseModel):
    type:        str = "heartbeat"
    server_time: float
    latency_ms:  Optional[float] = None


class WSErrorMessage(BaseModel):
    type:    str = "error"
    message: str


# ─── Report ─────────────────────────────────────────────

class ClinicalReport(BaseModel):
    """Laporan klinis terintegrasi dari satu sesi assessment."""
    session_id:           str
    patient_id:           str
    timestamp:            datetime
    instruction:          str

    # Asimetri
    meanASI:              float = 0.0
    maxASI:               float = 0.0
    shoulder_angle_L_mean: float = 0.0
    shoulder_angle_R_mean: float = 0.0
    angle_asymmetry:      float = 0.0

    # Tremor
    dominant_freq:        Optional[float] = None
    tremor_amplitude:     Optional[float] = None
    tremor_duration_pct:  float = 0.0

    # Sit-to-Stand
    transition_duration:  Optional[float] = None
    transition_velocity:  Optional[float] = None

    # Klasifikasi
    stroke_risk:    RiskLevel = RiskLevel.NORMAL
    parkinson_risk: RiskLevel = RiskLevel.NORMAL
    sarcopenia_risk: RiskLevel = RiskLevel.NORMAL

    # AI Narrative
    ai_narrative: Optional[str] = None
