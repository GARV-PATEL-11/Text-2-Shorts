"""app/main.py — FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.core.logger import configure_root_logging
from app.core.stage_tracker import StageTracker
from app.graph.workflow import close_pipeline, init_pipeline


configure_root_logging(level=logging.INFO)

_EVICTION_INTERVAL_S = 600  # run eviction every 10 minutes


async def _eviction_loop() -> None:
    """Background task: periodically evict stale StageTracker sessions."""
    _logger = logging.getLogger(__name__)
    while True:
        await asyncio.sleep(_EVICTION_INTERVAL_S)
        evicted = StageTracker.evict_stale()
        if evicted:
            _logger.info("StageTracker: evicted %d stale session(s)", len(evicted))


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    await init_pipeline()
    eviction_task = asyncio.create_task(_eviction_loop())
    try:
        yield
    finally:
        eviction_task.cancel()
        try:
            await eviction_task
        except asyncio.CancelledError:
            pass
        await close_pipeline()


app = FastAPI(title="Text-2-Shorts", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )

app.include_router(router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
