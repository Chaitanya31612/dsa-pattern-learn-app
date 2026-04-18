import os
from google import genai
from google.genai import types
from .base import AIAnalyzerInterface, AIResponse, AIProvider


class GeminiAnalyzer(AIAnalyzerInterface):
    """Google Gemini API implementation using the new google-genai SDK."""

    MODELS = {
        "flash": "gemini-2.5-flash-lite",
        "flash-full": "gemini-2.5-flash",
        "pro": "gemini-1.5-pro",
    }

    def __init__(self, model: str = "flash"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        self.client = genai.Client(api_key=api_key)
        self._model_key = self.MODELS.get(model, model)
        self._provider = AIProvider.GEMINI

    @property
    def provider(self) -> AIProvider:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model_key

    def analyze(self, content: str, prompt: str, json_mode: bool = False) -> AIResponse:
        try:
            full_prompt = f"{prompt}\n\nContent:\n{content}"

            config_kwargs = {
                "temperature": 0.1,
                "max_output_tokens": 8192,
            }

            if json_mode:
                config_kwargs["response_mime_type"] = "application/json"

            response = self.client.models.generate_content(
                model=self._model_key,
                contents=full_prompt,
                config=types.GenerateContentConfig(**config_kwargs)
            )

            # Token counting
            tokens_used = 0
            if response.usage_metadata:
                # API usually returns integer counts
                tokens_used = response.usage_metadata.total_token_count

            return AIResponse(
                content=response.text,
                model=self._model_key,
                provider=self._provider,
                tokens_used=tokens_used
            )

        except Exception as e:
            return AIResponse(
                content="",
                model=self._model_key,
                provider=self._provider,
                success=False,
                error=str(e)
            )

    def extract_json(self, content: str, schema: str) -> AIResponse:
        """Gemini-specific JSON extraction using response_mime_type."""
        try:
            prompt = f"""Extract information according to this schema:
{schema}

Content:
{content}"""

            response = self.client.models.generate_content(
                model=self._model_key,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                )
            )

            return AIResponse(
                content=response.text,
                model=self._model_key,
                provider=self._provider
            )

        except Exception as e:
            # Fallback to base implementation
            return super().extract_json(content, schema)
