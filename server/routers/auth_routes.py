"""Authentication routes — API key-based device auth for clinical deployments."""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel

from core.security import (
    create_access_token,
    verify_token,
    get_api_key_from_env,
    sanitize_patient_id,
)
from models.database import Database

router = APIRouter()


class LoginRequest(BaseModel):
    api_key: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int


class VerifyResponse(BaseModel):
    valid: bool


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    if req.api_key != get_api_key_from_env():
        raise HTTPException(status_code=401, detail="Invalid API key")
    token = create_access_token(
        data={"device_id": "clinical-device", "role": "clinician"}
    )
    return LoginResponse(token=token, expires_in=86400)


@router.get("/verify", response_model=VerifyResponse)
async def verify(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    token = authorization.removeprefix("Bearer ")
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return VerifyResponse(valid=True)