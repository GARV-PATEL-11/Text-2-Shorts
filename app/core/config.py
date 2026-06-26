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

    # ── Google Gemini ─────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_25_FLASH_MODEL: str = "gemini-2.5-flash"
    GEMINI_3_FLASH_MODEL: str = "gemini-3-flash"
    GEMINI_35_FLASH_MODEL: str = "gemini-3.5-flash"

    # ── S3 ────────────────────────────────────────────────────────────────────
    S3_BUCKET_NAME: str = ""
    S3_KEY_PREFIX: str = "video-previews"


settings = Settings()
