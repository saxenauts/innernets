from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv


Role = Literal["system", "user", "assistant", "tool"]


class Message(BaseModel):
    role: Role
    content: str


class JsonSchema(BaseModel):
    type: str = Field(default="object")
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additionalProperties: bool = Field(default=False)


class FunctionSpec(BaseModel):
    name: str
    description: str
    parameters: JsonSchema


class InvokeOptions(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    tool_choice: Literal["auto", "required", "none", "function"] = "function"
    strict: bool = True
    user: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Usage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class InvokeResult(BaseModel):
    id: Optional[str] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None
    usage: Usage = Field(default_factory=Usage)
    raw: Optional[Dict[str, Any]] = None


class StructuredRequest(BaseModel):
    instruction: str
    context: Any
    schema_name: str = "output"
    out_schema: JsonSchema
    system: Optional[str] = None
    pydantic_model: Optional[Any] = None


class StructuredResult(BaseModel):
    id: Optional[str] = None
    model: Optional[str] = None
    output: Dict[str, Any] = Field(default_factory=dict)
    usage: Usage = Field(default_factory=Usage)
    raw: Optional[Dict[str, Any]] = None


class ProviderError(BaseModel):
    code: str
    message: str
    status: Optional[int] = None
    retry_after: Optional[float] = None
    provider_code: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class ProviderConfig(BaseModel):
    provider: Literal["azure_openai", "openai"] = "azure_openai"
    # Azure
    azure_endpoint: Optional[str] = None
    azure_api_version: Optional[str] = None
    azure_api_key: Optional[str] = None
    azure_deployment: Optional[str] = None
    # OpenAI
    openai_api_key: Optional[str] = None
    openai_org: Optional[str] = None
    openai_base_url: Optional[str] = None

    @classmethod
    def from_env(cls, provider: Optional[str] = None) -> "ProviderConfig":
        # Ensure .env is loaded if present
        load_dotenv(os.getenv("DOTENV_PATH", ".env"), override=False)
        p = provider or os.getenv("PROVIDER", "azure_openai")
        if p == "azure_openai":
            return cls(
                provider=p,
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                azure_api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
                azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            )
        else:
            return cls(
                provider=p,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                openai_org=os.getenv("OPENAI_ORG"),
                openai_base_url=os.getenv("OPENAI_BASE_URL"),
            )
