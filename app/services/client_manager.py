"""client_manager.py"""

import boto3
from groq import Groq
from app.core.config import settings


class BedrockClientManager:

    _client = None

    @classmethod
    def get_client(cls) -> boto3.client:
        if cls._client is None:
            cls._client = boto3.client(
                "bedrock-runtime",
                access_key=settings.AWS_ACCESS_KEY_ID,
                secret_key=settings.SECRET_KEY,
                region_name=settings.AWS_SECRET_ACCESS_KEY,
                )

        return cls._client


class GroqClientManager:
    _client: Groq | None = None

    @classmethod
    def get_client(cls) -> Groq:
        if cls._client is None:
            cls._client = Groq(
                api_key=settings.GROQ_API_KEY,
                )

        return cls._client

