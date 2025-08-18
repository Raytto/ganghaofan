from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..config import get_passphrase_map, get_mock_settings

router = APIRouter()


class ResolveReq(BaseModel):
    passphrase: str


@router.post("/env/resolve")
def resolve_passphrase(body: ResolveReq):
    p = (body.passphrase or "").strip()
    if not p:
        raise HTTPException(status_code=400, detail="passphrase required")
    m = get_passphrase_map()
    if p not in m:
        raise HTTPException(status_code=400, detail="口令没对上")
    return {"key": m[p]}


@router.get("/env/mock")
def get_mock_env():
    """Dev helper: return current mock auth settings."""
    return get_mock_settings()
