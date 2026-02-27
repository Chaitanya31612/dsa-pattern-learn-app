import ollama
from .base import AIAnalyzerInterface, AIResponse, AIProvider


class OllamaAnalyzer(AIAnalyzerInterface):
    """Local Ollama implementation."""

    def __init__(self, model: str = "phi3:latest"):
        self._model = model
        self._provider = AIProvider.OLLAMA

    @property
    def provider(self) -> AIProvider:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    def analyze(self, content: str, prompt: str) -> AIResponse:
        try:
            full_prompt = f"{prompt}\n\nContent:\n{content}"

            response = ollama.chat(
                model=self._model,
                messages=[{"role": "user", "content": full_prompt}]
            )

            return AIResponse(
                content=response.message.content,
                model=self._model,
                provider=self._provider
            )

        except Exception as e:
            return AIResponse(
                content="",
                model=self._model,
                provider=self._provider,
                success=False,
                error=str(e)
            )
