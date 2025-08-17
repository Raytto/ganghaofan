from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from ..utils.security import create_token

router = APIRouter()


class LoginReq(BaseModel):
    code: str


@router.post("/auth/login")
def login(req: LoginReq):
    # TODO: integrate with WeChat code2session; for now, simulate open_id
    open_id = f"dev_{req.code}"
    token = create_token(open_id)
    # user payload minimal
    return {
        "token": token,
        "user": {
            "id": None,
            "nickname": None,
            "avatar": None,
            "is_admin": False,
        },
    }
