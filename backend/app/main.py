from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import auth, repos, chat, share

app = FastAPI(title="Codebase Chat", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(repos.router, prefix="/repos", tags=["repos"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(share.router, prefix="/share", tags=["share"])


@app.get("/health")
async def health():
    return {"status": "ok"}
