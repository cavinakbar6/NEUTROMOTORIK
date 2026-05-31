"""
Session Replay — Store and replay raw landmark data for debugging and clinical review.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class LandmarkFrame(BaseModel):
    frame_number: int = Field(..., description="Frame index in session")
    timestamp: float = Field(..., description="Timestamp in seconds from session start")
    landmarks_json: str = Field(..., description="JSON-encoded list of Landmark dicts")


class ReplayData(BaseModel):
    session_id: str
    frames: List[LandmarkFrame]
    total_frames: int
    duration_s: float