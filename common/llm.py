"""Shared LLM factory for all agents.

Uses OpenRouter as an OpenAI-compatible API, so any provider's model
can be selected via the OPENROUTER_MODEL env var.
"""

import os

from langchain_openai import ChatOpenAI

_LANGUAGE_INSTRUCTIONS = {
    "vi": "Luôn trả lời bằng tiếng Việt.",
    "en": "Always respond in English.",
}


def language_instruction() -> str:
    """Return a system-prompt suffix for the configured response language."""
    lang = os.getenv("RESPONSE_LANGUAGE", "vi").lower()
    return _LANGUAGE_INSTRUCTIONS.get(lang, _LANGUAGE_INSTRUCTIONS["vi"])


_llm_cache: dict[str, ChatOpenAI] = {}


def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI client pointed at the configured LLM provider (Mistral, OpenAI, or OpenRouter)."""
    # Create a unique key based on the environment configuration
    mistral_key = os.getenv("MISTRAL_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    
    if mistral_key:
        model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
        key = f"mistral:{model}:{mistral_key}"
    elif openrouter_key and not openai_key:
        model = os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
        key = f"openrouter:{model}:{openrouter_key}"
    else:
        model = os.getenv("OPENAI_MODEL") or os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
        key = f"openai:{model}:{openai_key or ''}"

    if key in _llm_cache:
        return _llm_cache[key]

    # 1. Kiểm tra Mistral AI
    if mistral_key:
        model = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
        llm = ChatOpenAI(
            model=model,
            api_key=mistral_key,
            base_url="https://api.mistral.ai/v1",
            max_tokens=1024,
            temperature=0.3,
        )
        _llm_cache[key] = llm
        return llm

    # 2. Kiểm tra OpenAI hoặc OpenRouter
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENAI_MODEL") or os.getenv("OPENROUTER_MODEL", "gpt-4o-mini")
    
    # Nếu dùng OpenRouter thì có base_url riêng, ngược lại dùng OpenAI mặc định
    if "openrouter" in model or (os.getenv("OPENROUTER_API_KEY") and not os.getenv("OPENAI_API_KEY")):
        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            max_tokens=1024,
            temperature=0.3,
        )
    else:
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            max_tokens=1024,
            temperature=0.3,
        )
    _llm_cache[key] = llm
    return llm