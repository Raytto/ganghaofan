from fastapi import FastAPI
from .routers import auth, users, meals, orders, logs
from .db import init_db
from fastapi import FastAPI

app = FastAPI(title="GangHaoFan API", version="0.1.0")


@app.on_event("startup")
def _on_startup():
    # Initialize DB (create tables if not exists)
    init_db()


# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(meals.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(logs.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"ok": True}
