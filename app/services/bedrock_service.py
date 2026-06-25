# service.py

import json

from app.models import BedrockResponse
from pydantic import BaseModel

from app.services.client_manager import BedrockClientManager


class BedrockService:

    def __init__(self):
        self.client = BedrockClientManager.get_client()

    async def invoke(
            self,
            prompt: str,
            model_id: str,
            temperature: float = 0.3,
            max_tokens: int = 4096,
            ) -> BedrockResponse:
        body = {
                "messages": [
                        {
                                "role": "user",
                                "content": [
                                        {
                                                "text": prompt,
                                                },
                                        ],
                                },
                        ],
                "inferenceConfig": {
                        "temperature": temperature,
                        "maxTokens": max_tokens,
                        },
                }

        response = self.client.converse(
                modelId=model_id,
                messages=body["messages"],
                inferenceConfig=body["inferenceConfig"],
                )

        output = response["output"]

        text = output["message"]["content"][0]["text"]

        usage = response.get("usage", {})

        return BedrockResponse(
                content=text,
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
                stop_reason=response.get("stopReason"),
                )

    async def invoke_structured(
            self,
            prompt: str,
            schema: type[BaseModel],
            model_id: str,
            ) -> schema:
        schema_json = schema.model_json_schema()

        structured_prompt = f"""
            Return ONLY valid JSON.
            
            Schema:
            {json.dumps(schema_json, indent=2)}
            
            User Request:
            {prompt}
            """

        response = await self.invoke(
                prompt=structured_prompt,
                model_id=model_id,
                )

        return schema.model_validate_json(response.content)
