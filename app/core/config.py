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

    # ── Cloudflare Workers AI ─────────────────────────────────────────────────
    CLOUDFLARE_AUTH_TOKEN: str = os.environ.get("CLOUDFLARE_AUTH_TOKEN", "")
    CLOUDFLARE_ACCOUNT_ID: str = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    # Reasoning / general tasks (outline, planning, refinement)
    CLOUDFLARE_PRIMARY_MODEL: str = "gemini-2.5-flash"
    # Code generation and render debugging
    CLOUDFLARE_CODING_MODEL: str = "gemini-2.5-flash"

    # ── Cloudflare fallback (used when primary model exhausted) ───────────────
    CLOUDFLARE_FALLBACK_MODEL: str = "gemini-2.5-flash"

    # ── Subprocess timeouts ───────────────────────────────────────────────────
    MANIM_TIMEOUT_S: int = 300  # per render attempt
    FFMPEG_TIMEOUT_S: int = 120  # video assembly

    # ── Gemini (registered but unused — kept so import doesn't crash) ─────────
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

    # ── S3 ────────────────────────────────────────────────────────────────────
    S3_BUCKET_NAME: str = ""
    S3_KEY_PREFIX: str = "video-previews"


settings = Settings()
