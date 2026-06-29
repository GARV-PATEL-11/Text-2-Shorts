"""app/main.py — FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.core.logger import configure_root_logging


configure_root_logging(level=logging.INFO)

app = FastAPI(title="Text-2-Shorts", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    )

app.include_router(router)
