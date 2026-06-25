from pydantic import BaseModel


class BedrockResponse(BaseModel):
    content: str
    input_tokens: int
    output_tokens: int
    stop_reason: str | None = None
