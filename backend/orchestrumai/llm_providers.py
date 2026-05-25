"""Multi-provider LLM configuration (BrowserOS-style catalog + ADK LiteLlm)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal

log = logging.getLogger(__name__)

AuthType = Literal["api_key", "local", "oauth", "built_in"]
ProviderStatus = Literal["available", "needs_config", "coming_soon", "connected"]


@dataclass(frozen=True)
class ModelOption:
    id: str
    label: str
    litellm_id: str | None = None  # None = use id as native gemini model name


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    name: str
    description: str
    auth_type: AuthType
    env_vars: tuple[str, ...]
    models: tuple[ModelOption, ...]
    docs_url: str = ""
    # LiteLLM model prefix, e.g. "openai/" -> openai/gpt-4o
    litellm_prefix: str | None = None
    # Use ADK native Gemini (google.genai) instead of LiteLLM
    native_gemini: bool = False
    # Env var for OpenAI-compatible base URL (Ollama, LM Studio)
    api_base_env: str | None = None
    default_api_base: str | None = None
    # Dummy API key for local OpenAI-compatible servers
    local_api_key: str = "local"


PROVIDER_CATALOG: tuple[ProviderDefinition, ...] = (
    ProviderDefinition(
        id="gemini",
        name="Google Gemini",
        description="Google AI Studio / Gemini API (native ADK)",
        auth_type="api_key",
        env_vars=("GOOGLE_API_KEY",),
        native_gemini=True,
        models=(
            ModelOption("gemini-2.5-flash", "Gemini 2.5 Flash"),
            ModelOption("gemini-2.5-pro", "Gemini 2.5 Pro"),
            ModelOption("gemini-2.0-flash", "Gemini 2.0 Flash"),
        ),
        docs_url="https://aistudio.google.com/apikey",
    ),
    ProviderDefinition(
        id="openai",
        name="OpenAI",
        description="GPT-4o, o-series, and other OpenAI models via API key",
        auth_type="api_key",
        env_vars=("OPENAI_API_KEY",),
        litellm_prefix="openai/",
        models=(
            ModelOption("gpt-4o", "GPT-4o", "openai/gpt-4o"),
            ModelOption("gpt-4o-mini", "GPT-4o mini", "openai/gpt-4o-mini"),
            ModelOption("o3-mini", "o3 mini", "openai/o3-mini"),
        ),
        docs_url="https://platform.openai.com/api-keys",
    ),
    ProviderDefinition(
        id="anthropic",
        name="Claude (Anthropic)",
        description="Claude models via Anthropic API key",
        auth_type="api_key",
        env_vars=("ANTHROPIC_API_KEY",),
        litellm_prefix="anthropic/",
        models=(
            ModelOption(
                "claude-sonnet-4-20250514",
                "Claude Sonnet 4",
                "anthropic/claude-sonnet-4-20250514",
            ),
            ModelOption(
                "claude-3-5-sonnet-20241022",
                "Claude 3.5 Sonnet",
                "anthropic/claude-3-5-sonnet-20241022",
            ),
            ModelOption(
                "claude-3-5-haiku-20241022",
                "Claude 3.5 Haiku",
                "anthropic/claude-3-5-haiku-20241022",
            ),
        ),
        docs_url="https://console.anthropic.com/settings/keys",
    ),
    ProviderDefinition(
        id="openrouter",
        name="OpenRouter",
        description="Route to many models with one OpenRouter API key",
        auth_type="api_key",
        env_vars=("OPENROUTER_API_KEY",),
        litellm_prefix="openrouter/",
        models=(
            ModelOption(
                "anthropic/claude-3.5-sonnet",
                "Claude 3.5 Sonnet (OR)",
                "openrouter/anthropic/claude-3.5-sonnet",
            ),
            ModelOption("openai/gpt-4o", "GPT-4o (OR)", "openrouter/openai/gpt-4o"),
            ModelOption(
                "google/gemini-2.5-flash",
                "Gemini 2.5 Flash (OR)",
                "openrouter/google/gemini-2.5-flash",
            ),
        ),
        docs_url="https://openrouter.ai/keys",
    ),
    ProviderDefinition(
        id="ollama",
        name="Ollama",
        description="Local models via Ollama (no API key)",
        auth_type="local",
        env_vars=(),
        litellm_prefix="ollama/",
        api_base_env="OLLAMA_HOST",
        default_api_base="http://127.0.0.1:11434",
        models=(
            ModelOption("llama3.1", "Llama 3.1", "ollama/llama3.1"),
            ModelOption("mistral", "Mistral", "ollama/mistral"),
            ModelOption("qwen2.5", "Qwen 2.5", "ollama/qwen2.5"),
        ),
        docs_url="https://docs.browseros.com/features/ollama",
    ),
    ProviderDefinition(
        id="lmstudio",
        name="LM Studio",
        description="Local OpenAI-compatible server (LM Studio)",
        auth_type="local",
        env_vars=(),
        litellm_prefix="openai/",
        api_base_env="LM_STUDIO_BASE_URL",
        default_api_base="http://127.0.0.1:1234/v1",
        models=(
            ModelOption("local-model", "Loaded model", "openai/local-model"),
        ),
        docs_url="https://docs.browseros.com/features/lm-studio",
    ),
    ProviderDefinition(
        id="chatgpt_oauth",
        name="ChatGPT Plus / Pro",
        description="Use your ChatGPT subscription via OAuth (same flow as BrowserOS / Codex CLI)",
        auth_type="oauth",
        env_vars=(),
        models=(
            ModelOption("gpt-5.2", "GPT-5.2"),
            ModelOption("gpt-5.2-codex", "GPT-5.2 Codex"),
            ModelOption("gpt-5.1-codex-max", "GPT-5.1 Codex Max"),
            ModelOption("gpt-4.1", "GPT-4.1"),
        ),
        docs_url="https://docs.browseros.com/features/chatgpt-pro-oauth",
    ),
)


def get_provider(provider_id: str) -> ProviderDefinition | None:
    for p in PROVIDER_CATALOG:
        if p.id == provider_id:
            return p
    return None


def _env_configured(var: str) -> bool:
    return bool(os.environ.get(var, "").strip())


def provider_connection_status(provider: ProviderDefinition) -> ProviderStatus:
    if provider.auth_type == "oauth":
        if provider.id == "chatgpt_oauth":
            from .chatgpt_oauth import is_connected

            return "connected" if is_connected() else "needs_config"
        return "coming_soon"
    if provider.auth_type == "local":
        return "available"
    if provider.native_gemini and _env_configured("GOOGLE_API_KEY"):
        return "connected"
    if provider.env_vars and all(_env_configured(v) for v in provider.env_vars):
        return "connected"
    if provider.env_vars:
        return "needs_config"
    return "available"


def resolve_litellm_model_id(provider: ProviderDefinition, model_id: str) -> str:
    for m in provider.models:
        if m.id == model_id:
            if m.litellm_id:
                return m.litellm_id
            if provider.litellm_prefix:
                return f"{provider.litellm_prefix}{m.id}"
            return m.id
    if provider.litellm_prefix:
        return f"{provider.litellm_prefix}{model_id}"
    return model_id


@dataclass
class ResolvedModel:
    provider_id: str
    model_id: str
    # Value passed to LlmAgent.model (str or LiteLlm instance)
    adk_model: Any
    display_name: str


def build_adk_model(provider_id: str, model_id: str | None = None) -> ResolvedModel:
    """Build ADK-compatible model for LlmAgent from provider + model selection."""
    from .provider_settings import get_provider_settings

    settings = get_provider_settings()
    pid = provider_id or settings.default_provider_id
    provider = get_provider(pid)
    if provider is None:
        provider = get_provider("gemini")
        pid = "gemini"
    assert provider is not None

    mid = model_id or settings.default_model_id
    if not any(m.id == mid for m in provider.models):
        mid = provider.models[0].id

    model_label = next((m.label for m in provider.models if m.id == mid), mid)

    if provider.native_gemini:
        if not STUB_CHECK_SKIP_API_KEY() and not _env_configured("GOOGLE_API_KEY"):
            log.warning("GOOGLE_API_KEY not set; agent may fail without stub mode")
        return ResolvedModel(
            provider_id=pid,
            model_id=mid,
            adk_model=mid,
            display_name=f"{provider.name} / {model_label}",
        )

    if provider.auth_type == "oauth":
        if provider.id != "chatgpt_oauth":
            raise ValueError(f"{provider.name} OAuth is not supported yet.")
        _ensure_oauth_codex()
        from .chatgpt_oauth import get_valid_tokens
        from .codex_adk_llm import CodexAdkLlm

        get_valid_tokens(interactive=True)
        return ResolvedModel(
            provider_id=pid,
            model_id=mid,
            adk_model=CodexAdkLlm(model=mid),
            display_name=f"{provider.name} / {model_label}",
        )

    _ensure_litellm()
    from google.adk.models.lite_llm import LiteLlm

    litellm_model = resolve_litellm_model_id(provider, mid)
    extra: dict[str, Any] = {}
    if provider.api_base_env:
        base = os.environ.get(provider.api_base_env, provider.default_api_base or "")
        if base:
            extra["api_base"] = base.rstrip("/")
            if provider.id == "lmstudio" and not extra["api_base"].endswith("/v1"):
                extra["api_base"] = extra["api_base"] + "/v1"
    if provider.auth_type == "local":
        extra["api_key"] = provider.local_api_key

    return ResolvedModel(
        provider_id=pid,
        model_id=mid,
        adk_model=LiteLlm(model=litellm_model, **extra),
        display_name=f"{provider.name} / {model_label}",
    )


def STUB_CHECK_SKIP_API_KEY() -> bool:
    from .config import STUB_RUN

    return STUB_RUN


def _ensure_oauth_codex() -> None:
    try:
        import oauth_codex  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Install oauth-codex for ChatGPT OAuth: pip install 'orchestrumai[llm]'"
        ) from exc


def _ensure_litellm() -> None:
    try:
        import litellm  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Install litellm for non-Gemini providers: pip install 'orchestrumai[llm]'"
        ) from exc


def catalog_for_api() -> list[dict[str, Any]]:
    """Serialize provider catalog for the settings UI."""
    from .provider_settings import get_provider_settings

    settings = get_provider_settings()
    out: list[dict[str, Any]] = []
    for p in PROVIDER_CATALOG:
        status = provider_connection_status(p)
        out.append(
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "auth_type": p.auth_type,
                "status": status,
                "env_vars": list(p.env_vars),
                "docs_url": p.docs_url,
                "models": [{"id": m.id, "label": m.label} for m in p.models],
                "is_default": p.id == settings.default_provider_id,
            }
        )
    return out


def apply_litellm_env() -> None:
    """Set LiteLLM-friendly env aliases from stored settings (optional keys in DB)."""
    from .provider_settings import get_provider_settings

    settings = get_provider_settings()
    for key, value in settings.api_keys.items():
        if value and key not in os.environ:
            os.environ[key] = value
