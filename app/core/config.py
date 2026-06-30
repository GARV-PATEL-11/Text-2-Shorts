"""config.py"""

import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings


load_dotenv()


class Settings(BaseSettings):
    # ── AWS ───────────────────────────────────────────────────────────────────
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

    # ── Bedrock ───────────────────────────────────────────────────────────────
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"

    # ── Gemini (model selection) ───────────────────────────────────────────────
    # API keys are managed by PoolGate via GeminiConfig.from_env().
    # Required env vars for the key pool (read by PoolGate, not this class):
    #   TOTAL_GEMINI_KEYS=<n>
    #   GEMINI_API_KEY_01=<key>  …  GEMINI_API_KEY_<n>=<key>
    # Optional pool tuning (PoolGate defaults shown):
    #   GEMINI_MAX_RPM=5            GEMINI_MAX_ACTIVE=5
    #   GEMINI_COOLDOWN_SECS=60     GEMINI_FAILURE_THRESHOLD=3
    #   GEMINI_BATCH_CONCURRENCY=10 GEMINI_MAX_RETRIES=3
    #   GEMINI_BASE_BACKOFF=1.0     GEMINI_MAX_BACKOFF=30.0
    #   GEMINI_SESSION_TTL_HOURS=24
    #   GEMINI_DEBUG=false          GEMINI_LOG_LEVEL=INFO
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-2.5-flash"

    # ── Subprocess timeouts ───────────────────────────────────────────────────
    MANIM_TIMEOUT_S: int = 300  # per render attempt
    FFMPEG_TIMEOUT_S: int = 120  # video assembly

    # ── S3 ────────────────────────────────────────────────────────────────────
    S3_BUCKET_NAME: str = ""
    S3_KEY_PREFIX: str = "video-previews"


settings = Settings()
