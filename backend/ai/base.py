from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class AIProvider(Enum):
    GROQ = "groq"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class AIResponse:
    """Standardized response from any AI provider."""
    content: str
    model: str
    provider: AIProvider
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


class AIAnalyzerInterface(ABC):
    """
    Interface for AI analyzers.
    All implementations must provide these methods.
    """

    @property
    @abstractmethod
    def provider(self) -> AIProvider:
        """Return the provider enum."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        pass

    @abstractmethod
    def analyze(self, content: str, prompt: str) -> AIResponse:
        """
        Analyze content with a given prompt.

        Args:
            content: The text content to analyze
            prompt: Instructions for the AI

        Returns:
            AIResponse with the result
        """
        pass

    def extract_json(self, content: str, schema: str) -> AIResponse:
        """
        Extract structured JSON from content.
        Default implementation uses analyze() with JSON prompt.
        Can be overridden for provider-specific JSON modes.
        """
        prompt = f"""Extract information and return ONLY valid JSON, no markdown.

Schema:
{schema}

Rules:
- Return ONLY the JSON object
- Use null for missing fields
- Be precise and factual"""

        return self.analyze(content, prompt)
