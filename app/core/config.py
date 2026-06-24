"""config.py"""

from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):

    AWS_REGION: str = os.getenv("AWS_REGION")
    AWS_ACCESS_KEY_ID: str = os.environ.get("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: str = os.environ.get("AWS_SECRET_ACCESS_KEY")

    NOVA_MICRO_MODEL_ID: str = "us.amazon.nova-micro-v1:0"
    NOVA_LITE_MODEL_ID: str = "us.amazon.nova-lite-v1:0"
    NOVA_PRO_MODEL_ID: str = "us.amazon.nova-pro-v1:0"

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")


settings = Settings()