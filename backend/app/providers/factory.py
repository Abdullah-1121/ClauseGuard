"""Model factory — the single place model/provider choice is resolved.

The rest of the codebase asks for a *role* ("cheap" or "strong") and never
knows or cares which provider backs it. Swapping Groq -> OpenRouter -> local
Ollama is a config change, not a code change. Provider modules are imported
lazily so that selecting one provider never requires the others to be installed.
"""

from __future__ import annotations

from typing import Literal

from pydantic_ai.models import Model

from app.config import Settings, get_settings

Role = Literal["cheap", "strong"]


def _model_id(settings: Settings, role: Role) -> str:
    return settings.model_cheap if role == "cheap" else settings.model_strong


def build_model(role: Role, settings: Settings | None = None) -> Model:
    """Return a pydantic-ai Model for the given role, per configured provider."""
    settings = settings or get_settings()
    model_id = _model_id(settings, role)

    if settings.provider == "groq":
        from pydantic_ai.models.groq import GroqModel
        from pydantic_ai.providers.groq import GroqProvider

        return GroqModel(model_id, provider=GroqProvider(api_key=settings.groq_api_key))

    if settings.provider in ("ollama", "openrouter"):
        # Both are OpenAI-compatible HTTP endpoints.
        try:
            from pydantic_ai.models.openai import OpenAIChatModel as _OpenAIModel
        except ImportError:  # older pydantic-ai
            from pydantic_ai.models.openai import OpenAIModel as _OpenAIModel
        from pydantic_ai.providers.openai import OpenAIProvider

        if settings.provider == "ollama":
            provider = OpenAIProvider(base_url=settings.ollama_base_url, api_key="ollama")
        else:
            provider = OpenAIProvider(
                base_url=settings.openrouter_base_url, api_key=settings.openrouter_api_key
            )
        return _OpenAIModel(model_id, provider=provider)

    raise ValueError(f"Unknown provider: {settings.provider}")
