from __future__ import annotations

import json
from typing import Any, Dict, List

from openai import OpenAI

from ..types import (
    InvokeOptions,
    ProviderConfig,
    ProviderError,
    Usage,
    StructuredRequest,
    StructuredResult,
)
from ..provider_base import LLMProvider
from ..client import get_client


class AzureOpenAIProvider(LLMProvider):
    def __init__(self, cfg: ProviderConfig) -> None:
        super().__init__(cfg)
        if not (cfg.azure_endpoint and cfg.azure_api_version and cfg.azure_api_key and cfg.azure_deployment):
            raise ValueError("Azure OpenAI config incomplete: endpoint, api_version, api_key, deployment required")
        self._client: OpenAI = get_client(cfg)

    def map_error(self, err: Exception) -> ProviderError:
        # Generic fallback mapping
        return ProviderError(code="ProviderError", message=str(err))

    def _raise_err(self, err: Exception) -> Exception:
        pe = self.map_error(err)
        return RuntimeError(pe.model_dump_json())

    def _raise_status(self, status_code: int, body: Dict[str, Any]) -> Exception:
        message = body.get("error", {}).get("message") or body.get("message") or str(body)
        provider_code = body.get("error", {}).get("code") or str(status_code)
        pe = ProviderError(code="HTTPError", message=message, status=status_code, provider_code=provider_code)
        return RuntimeError(pe.model_dump_json())

    def structured(self, req: StructuredRequest, options: InvokeOptions) -> StructuredResult:  # type: ignore[override]
        # Chat Completions with JSON-only instruction and client-side validation
        instruction = req.instruction
        if req.context is not None:
            instruction = f"{req.instruction}\n\nContext:\n{json.dumps(req.context)[:4000]}"
        return self._structured_via_chat(instruction, req, options)

    def _structured_via_chat(self, instruction: str, req: StructuredRequest, options: InvokeOptions) -> StructuredResult:
        sys_prompt = "You must return a single JSON object only."
        # Minimal schema hint to improve fidelity (top-level + key nested arrays)
        if req.pydantic_model is not None:
            try:
                schema = req.pydantic_model.model_json_schema()  # type: ignore[attr-defined]
            except Exception:
                schema = req.pydantic_model.schema()  # type: ignore[attr-defined]
            properties = schema.get("properties", {}) or {}
            top_keys = list(properties.keys())
            sys_prompt += f" Allowed top-level keys: {top_keys}. Do not include extra keys at any level."
            for name, prop in properties.items():
                try:
                    if (prop.get("type") == "array") and isinstance(prop.get("items"), dict):
                        item_props = list((prop["items"].get("properties", {}) or {}).keys())
                        if item_props:
                            sys_prompt += f" For array '{name}', each item allowed keys: {item_props}."
                except Exception:
                    pass
            # Generic URL hint: if only domain provided, construct url
            sys_prompt += " If schema requires a URL and only a domain is present in context, construct it as 'https://<domain>/' ."
            # Generic integer hint to avoid fractional outputs where ints are expected
            sys_prompt += " If any field type is integer, output whole numbers only (no decimals)."
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": instruction + "\nReturn valid JSON only."},
        ]
        try:
            model_name = (self.cfg.azure_deployment or "").lower()
            params: Dict[str, Any] = {
                "model": self.cfg.azure_deployment,
                "messages": messages,
                "response_format": {"type": "json_object"},
            }
            # Azure gpt-5 requires temperature=1.0 (rejects 0.0)
            if "gpt-5" in model_name:
                params["temperature"] = 1.0
            else:
                temp = options.temperature if options.temperature is not None else 1.0
                params["temperature"] = temp
                if options.top_p is not None:
                    params["top_p"] = options.top_p
                if options.max_tokens is not None:
                    # For non gpt-5 chat completions, use standard max_tokens
                    params["max_tokens"] = options.max_tokens
            resp = self._client.chat.completions.create(**params)
        except Exception as e:
            # If Azure rejects response_format or extra field, try a minimal retry without them
            try:
                params.pop("response_format", None)
                resp = self._client.chat.completions.create(**params)
            except Exception:
                raise self._raise_err(e)

        try:
            content = resp.choices[0].message.content  # type: ignore[attr-defined]
            data = json.loads(content or "{}")
        except Exception as e:
            raise self._raise_err(e)

        # Validate client-side if pydantic model provided
        if req.pydantic_model is not None:
            try:
                model_inst = req.pydantic_model(**data)
                data = model_inst.model_dump(mode="json")
            except Exception as e:
                # One repair attempt: provide validation errors and ask for corrected JSON
                try:
                    err_text = str(e)
                    repair_system = sys_prompt + " Fix the JSON to satisfy validation exactly."
                    repair_user = (
                        instruction
                        + "\n\nValidation failed with the following errors:\n"
                        + err_text
                        + "\nReturn only the corrected JSON object; no commentary."
                    )
                    repair_msgs = [
                        {"role": "system", "content": repair_system},
                        {"role": "user", "content": repair_user},
                    ]
                    model_name = (self.cfg.azure_deployment or "").lower()
                    params2: Dict[str, Any] = {
                        "model": self.cfg.azure_deployment,
                        "messages": repair_msgs,
                        "response_format": {"type": "json_object"},
                    }
                    if "gpt-5" in model_name:
                        params2["temperature"] = 1.0
                    else:
                        params2["temperature"] = options.temperature if options.temperature is not None else 1.0
                    resp2 = self._client.chat.completions.create(**params2)
                    content2 = resp2.choices[0].message.content  # type: ignore[attr-defined]
                    data2 = json.loads(content2 or "{}")
                    model_inst2 = req.pydantic_model(**data2)
                    data = model_inst2.model_dump(mode="json")
                except Exception:
                    raise self._raise_err(e)

        usage = getattr(resp, "usage", None)
        return StructuredResult(
            id=getattr(resp, "id", None),
            model=self.cfg.azure_deployment,
            output=data if isinstance(data, dict) else {},
            usage=Usage(
                prompt_tokens=getattr(usage, "prompt_tokens", None) if usage else None,
                completion_tokens=getattr(usage, "completion_tokens", None) if usage else None,
                total_tokens=getattr(usage, "total_tokens", None) if usage else None,
            ),
            raw={"chat_completions": True},
        )
