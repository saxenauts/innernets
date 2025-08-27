from __future__ import annotations

from typing import Sequence
from .types import (
    FunctionSpec,
    InvokeOptions,
    InvokeResult,
    Message,
    ProviderConfig,
    StructuredRequest,
    StructuredResult,
)
from .provider_base import LLMProvider
from .providers.azure_openai import AzureOpenAIProvider


def get_provider(cfg: ProviderConfig) -> LLMProvider:
    if cfg.provider == "azure_openai":
        return AzureOpenAIProvider(cfg)
    raise ValueError(f"Unsupported provider: {cfg.provider}")


def structured(
    cfg: ProviderConfig,
    req: StructuredRequest,
    options: InvokeOptions,
) -> StructuredResult:
    provider = get_provider(cfg)
    return provider.structured(req, options)
