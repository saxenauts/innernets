from __future__ import annotations

from typing import Any
from openai import OpenAI
from .types import ProviderConfig


def get_client(cfg: ProviderConfig) -> OpenAI:
    if cfg.provider == "azure_openai":
        # Prefer AzureOpenAI client for Azure resources
        if not (cfg.azure_endpoint and cfg.azure_api_key and cfg.azure_api_version):
            raise ValueError("Azure OpenAI config incomplete: endpoint, api_version, api_key required")
        try:
            from openai import AzureOpenAI  # type: ignore

            client = AzureOpenAI(
                api_key=cfg.azure_api_key,
                api_version=cfg.azure_api_version,
                azure_endpoint=cfg.azure_endpoint.strip().rstrip("/"),
            )
            print(
                "[llm-client] Using AzureOpenAI",
                {"azure_endpoint": cfg.azure_endpoint, "api_version": cfg.azure_api_version},
            )
            return client
        except Exception:
            # Fallback to resource-scoped base URL with standard client
            endpoint = (cfg.azure_endpoint or "").strip().rstrip("/")
            base_url = f"{endpoint}/openai/v1/"
            client = OpenAI(
                api_key=cfg.azure_api_key,
                base_url=base_url,
                default_query={"api-version": cfg.azure_api_version},
                default_headers={"api-key": cfg.azure_api_key},
            )
            print(
                "[llm-client] Using OpenAI (resource-scoped base)",
                {"base_url": base_url, "api_version": cfg.azure_api_version},
            )
            return client
    # OpenAI native (not used yet, but wired for parity)
    return OpenAI(
        api_key=cfg.openai_api_key,
        base_url=cfg.openai_base_url,
        organization=cfg.openai_org,
    )
