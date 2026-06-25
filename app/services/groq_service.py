"""groq_service.py"""

from groq import Groq

from app.services.client_manager import GroqClientManager


class GroqService:

    def __init__(self):
        self.client: Groq = GroqClientManager.get_client()

    def invoke(
            self,
            *,
            model: str,
            system_prompt: str | None = None,
            user_prompt: str,
            temperature: float = 0.2,
            max_tokens: int = 4096,
            ) -> str:

        messages = []

        if system_prompt:
            messages.append(
                    {
                            "role": "system",
                            "content": system_prompt,
                            },
                    )

        messages.append(
                {
                        "role": "user",
                        "content": user_prompt,
                        },
                )

        # pyrefly: ignore [no-matching-overload]
        response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_completion_tokens=max_tokens,
                )

        return response.choices[0].message.content

    def invoke_structured(
            self,
            *,
            model: str,
            prompt: str,
            ) -> dict:

        response = self.client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                messages=[
                        {
                                "role": "user",
                                "content": prompt,
                                },
                        ],
                )

        import json

        return json.loads(
                response.choices[0].message.content,
                )
