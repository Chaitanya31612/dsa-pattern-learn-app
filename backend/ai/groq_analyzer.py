import os
import time
from groq import Groq
from .base import AIAnalyzerInterface, AIResponse, AIProvider


class GroqAnalyzer(AIAnalyzerInterface):
    """Groq API implementation."""

    MODELS = {
        "fast": "llama-3.1-8b-instant",
        "smart": "llama-3.3-70b-versatile",
        "mixtral": "mixtral-8x7b-32768",
    }

    def __init__(self, model: str = "smart", requests_per_minute: int = 25):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")

        self.client = Groq(api_key=api_key)
        self._model = self.MODELS.get(model, model)
        self._provider = AIProvider.GROQ

        # Rate limiting
        self.min_interval = 60.0 / requests_per_minute
        self.last_request = 0

    @property
    def provider(self) -> AIProvider:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    def _rate_limit(self):
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()

    def analyze(self, content: str, prompt: str, json_mode: bool = False) -> AIResponse:
        self._rate_limit()

        try:
            kwargs = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": content}
                ],
                "max_tokens": 4096,
                "temperature": 0.1,
            }

            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = self.client.chat.completions.create(**kwargs)


            return AIResponse(
                content=response.choices[0].message.content,
                model=self._model,
                provider=self._provider,
                tokens_used=response.usage.total_tokens
            )

        except Exception as e:
            return AIResponse(
                content="",
                model=self._model,
                provider=self._provider,
                success=False,
                error=str(e)
            )
