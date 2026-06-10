from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import get_settings
from app.services.worker import scheduler_worker

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="NovelMaker MVP API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def startup_event() -> None:
    if settings.embedded_worker_enabled:
        scheduler_worker.start(mode="embedded")


@app.on_event("shutdown")
def shutdown_event() -> None:
    scheduler_worker.stop()
