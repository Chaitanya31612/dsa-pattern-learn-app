import os
from typing import Optional
from .base import AIProvider, AIAnalyzerInterface
from .groq_analyzer import GroqAnalyzer
from .gemini_analyzer import GeminiAnalyzer
from .ollama_analyzer import OllamaAnalyzer


class AIAnalyzerFactory:
    """
    Factory for creating AI analyzer instances.

    Usage:
        analyzer = AIAnalyzerFactory.create(AIProvider.GEMINI, model="flash")
        analyzer = AIAnalyzerFactory.create_default()  # Auto-detect best available
    """

    _registry: dict[AIProvider, type[AIAnalyzerInterface]] = {
        AIProvider.GROQ: GroqAnalyzer,
        AIProvider.GEMINI: GeminiAnalyzer,
        AIProvider.OLLAMA: OllamaAnalyzer,
    }

    @classmethod
    def register(cls, provider: AIProvider, analyzer_class: type[AIAnalyzerInterface]):
        """Register a new analyzer class for a provider."""
        cls._registry[provider] = analyzer_class

    @classmethod
    def create(
        cls,
        provider: AIProvider,
        model: Optional[str] = None,
        **kwargs
    ) -> AIAnalyzerInterface:
        """
        Create an analyzer for the specified provider.

        Args:
            provider: The AI provider to use
            model: Optional model name (uses provider default if not specified)
            **kwargs: Additional arguments passed to the analyzer constructor
        """
        if provider not in cls._registry:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(cls._registry.keys())}")

        analyzer_class = cls._registry[provider]

        if model:
            return analyzer_class(model=model, **kwargs)
        return analyzer_class(**kwargs)

    @classmethod
    def create_default(cls) -> AIAnalyzerInterface:
        """
        Create analyzer using best available provider.
        Priority: Gemini > Groq > Ollama
        """
        # Check Gemini first (best rate limits)
        if os.getenv("GEMINI_API_KEY"):
            return cls.create(AIProvider.GEMINI)

        # Check Groq second
        if os.getenv("GROQ_API_KEY"):
            return cls.create(AIProvider.GROQ)

        # Fallback to Ollama (local, always available)
        return cls.create(AIProvider.OLLAMA)

    @classmethod
    def available_providers(cls) -> list[AIProvider]:
        """List providers that have valid configuration."""
        available = []

        if os.getenv("GEMINI_API_KEY"):
            available.append(AIProvider.GEMINI)
        if os.getenv("GROQ_API_KEY"):
            available.append(AIProvider.GROQ)

        # Ollama is always "available" (local)
        available.append(AIProvider.OLLAMA)

        return available
