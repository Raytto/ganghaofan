from fastapi import Depends, HTTPException, Header
from jose import jwt

SECRET = "dev-secret-key-change-me"
ALGO = "HS256"


def create_token(open_id: str) -> str:
    return jwt.encode({"open_id": open_id}, SECRET, algorithm=ALGO)


async def get_open_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        # allow dev without token? could be disabled later
        raise HTTPException(401, "missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
        return payload.get("open_id")
    except Exception:
        raise HTTPException(401, "invalid token")
