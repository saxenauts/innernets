from __future__ import annotations

from typing import Sequence
from .types import (
    InvokeOptions,
    ProviderConfig,
    ProviderError,
    StructuredRequest,
    StructuredResult,
)


class LLMProvider:
    def __init__(self, cfg: ProviderConfig) -> None:
        self.cfg = cfg

    def map_error(self, err: Exception) -> ProviderError:
        raise NotImplementedError

    def structured(
        self,
        req: StructuredRequest,
        options: InvokeOptions,
    ) -> StructuredResult:
        """Return a validated JSON object conforming to req.schema.

        Providers implement OpenAI-style Structured Outputs when available; fallback to
        tool/function call + parsing when necessary.
        """
        raise NotImplementedError
