"""FastAPI 동기화 서버 진입점."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from api import notes, pdfs, sync, tags
from auth import create_token
from database_server import init_server_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_server_db()
    yield


app = FastAPI(title="Zettelkasten Sync Server", lifespan=lifespan)

app.include_router(notes.router, prefix="/api")
app.include_router(tags.router,  prefix="/api")
app.include_router(pdfs.router,  prefix="/api")
app.include_router(sync.router,  prefix="/api")


class TokenRequest(BaseModel):
    device_id: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@app.post("/api/auth/token", response_model=TokenResponse)
def issue_token(req: TokenRequest) -> TokenResponse:
    """등록된 기기에 JWT 를 발급한다(ALLOWED_DEVICES 로 제한)."""
    return TokenResponse(access_token=create_token(req.device_id))


@app.get("/api/health")
async def health():
    return {"status": "ok"}
