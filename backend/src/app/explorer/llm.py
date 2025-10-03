from __future__ import annotations

import os
import json
from typing import Any, Dict, Type, Tuple

from openai import OpenAI
from pydantic import BaseModel


def _build_base_url() -> str:
    # Prefer explicit base URL; else construct from resource name
    base_url = (
        os.getenv("AZURE_OPENAI_BASE_URL")
        or os.getenv("AZURE_OPENAI_ENDPOINT")
        or os.getenv("OPENAI_BASE_URL")
    )
    if base_url:
        # Normalize and ensure Azure v1 path
        base_url = base_url.rstrip("/")
        if not base_url.endswith("openai/v1"):
            base_url = base_url + "/openai/v1"
        base_url += "/"
        return base_url
    resource = os.getenv("AZURE_OPENAI_RESOURCE")
    if resource:
        return f"https://{resource}.openai.azure.com/openai/v1/"
    # Fallback: assume standard OpenAI
    return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/")


def get_openai_client() -> OpenAI:
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing AZURE_OPENAI_API_KEY (or OPENAI_API_KEY)")
    base_url = _build_base_url()
    return OpenAI(api_key=api_key, base_url=base_url)


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
    """Compute simple cost given env-configured pricing.

    Environment variables (USD per 1K tokens):
    - SURFER_INPUT_PRICE_PER_1K
    - SURFER_OUTPUT_PRICE_PER_1K
    Fallback to 0 if unset.
    """
    # Defaults (USD per 1K tokens) for known models when env is unset/zero
    DEFAULTS_PER_1K = {
        "gpt-5": (0.00125, 0.01),  # $1.25 / 1M input, $10 / 1M output
    }

    def _env_price(var: str) -> float:
        try:
            v = os.getenv(var)
            if v is None:
                return 0.0
            f = float(v)
            return f
        except Exception:
            return 0.0

    inp = _env_price("SURFER_INPUT_PRICE_PER_1K")
    out = _env_price("SURFER_OUTPUT_PRICE_PER_1K")

    if (inp == 0.0 and out == 0.0) or inp < 0 or out < 0:
        m = (model or "").lower()
        for key, (di, do) in DEFAULTS_PER_1K.items():
            if key in m:
                inp, out = di, do
                break
    input_cost = (input_tokens / 1000.0) * inp
    output_cost = (output_tokens / 1000.0) * out
    return {
        "input_cost_usd": round(input_cost, 6),
        "output_cost_usd": round(output_cost, 6),
        "total_cost_usd": round(input_cost + output_cost, 6),
    }


def parse_with_schema(
    client: OpenAI,
    model: str,
    system_text: str,
    user_text: str,
    pyd_model: Type[BaseModel],
    *,
    reasoning_effort: str | None = "low",
    text_verbosity: str | None = "low"
) -> Tuple[BaseModel, Dict[str, Any]]:
    """Call Responses API and parse into the given Pydantic model.

    Tries responses.parse(text_format=Model). If unavailable, falls back to
    responses.create + response_format json_schema and model_validate_json.
    """
    # Prefer SDK helper if available (supports usage)
    parse_attr = getattr(client.responses, "parse", None)
    if callable(parse_attr):
        resp = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            text_format=pyd_model,
            reasoning=( {"effort": reasoning_effort} if reasoning_effort else None ),
            text=( {"verbosity": text_verbosity} if text_verbosity else None )
        )
        parsed = pyd_model.model_validate(resp.output_parsed)
        usage_obj = getattr(resp, "usage", None) or {}
        try:
            input_tokens = int(getattr(usage_obj, "input_tokens", 0) or usage_obj.get("input_tokens", 0) or 0)
            output_tokens = int(getattr(usage_obj, "output_tokens", 0) or usage_obj.get("output_tokens", 0) or 0)
        except Exception:
            input_tokens, output_tokens = 0, 0
        cost = _compute_cost(model, input_tokens, output_tokens)
        usage = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            **cost,
        }
        return parsed, usage

    # Fallback: responses.create (some SDKs may not accept response_format)
    schema = pyd_model.model_json_schema()
    name = pyd_model.__name__
    rf = {
        "type": "json_schema",
        "json_schema": {"name": name, "schema": schema, "strict": True},
    }
    try:
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            response_format=rf,
            reasoning=( {"effort": reasoning_effort} if reasoning_effort else None ),
            text=( {"verbosity": text_verbosity} if text_verbosity else None ),
        )
    except TypeError:
        resp = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_text},
                {"role": "user", "content": user_text},
            ],
            reasoning=( {"effort": reasoning_effort} if reasoning_effort else None ),
            text=( {"verbosity": text_verbosity} if text_verbosity else None ),
        )
    parsed = pyd_model.model_validate_json(resp.output_text)
    usage_obj = getattr(resp, "usage", None) or {}
    try:
        input_tokens = int(getattr(usage_obj, "input_tokens", 0) or usage_obj.get("input_tokens", 0) or 0)
        output_tokens = int(getattr(usage_obj, "output_tokens", 0) or usage_obj.get("output_tokens", 0) or 0)
    except Exception:
        input_tokens, output_tokens = 0, 0
    cost = _compute_cost(model, input_tokens, output_tokens)
    usage = {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        **cost,
    }
    return parsed, usage
