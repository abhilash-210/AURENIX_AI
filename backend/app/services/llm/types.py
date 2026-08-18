"""
Domain types and data models for the LLM Gateway.
"""

from __future__ import annotations

from typing import Generic, Literal, TypeVar
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T", bound=BaseModel)

ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    """A single turn message in a chat conversation."""

    role: ChatRole = Field(description="Role of the message author")
    content: str = Field(description="Text content of the message")

    model_config = ConfigDict(frozen=True)


class CompletionOptions(BaseModel):
    """Options and hyper-parameters for LLM completion requests."""

    model: str | None = Field(
        default=None,
        description="Target model override (if None, provider default is used)",
    )
    temperature: float | None = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    max_tokens: int | None = Field(
        default=1024,
        ge=1,
        description="Maximum tokens to generate",
    )
    top_p: float | None = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability threshold",
    )
    timeout: float | None = Field(
        default=None,
        ge=0.1,
        description="Request timeout in seconds",
    )

    model_config = ConfigDict(extra="ignore")


class UsageInfo(BaseModel):
    """Token consumption statistics for a completion request."""

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class ChatCompletionResponse(BaseModel):
    """Complete non-streaming LLM chat response payload."""

    content: str = Field(description="Generated assistant text response")
    role: ChatRole = Field(default="assistant", description="Message role")
    model: str = Field(description="Model used for generation")
    provider: str = Field(description="Provider name (e.g. openai, anthropic, mock)")
    usage: UsageInfo = Field(default_factory=UsageInfo, description="Token usage details")
    finish_reason: str | None = Field(default="stop", description="Completion termination reason")


class ChatCompletionChunk(BaseModel):
    """A single incremental delta chunk in a streaming chat response."""

    delta: str = Field(description="Incremental text delta")
    finish_reason: str | None = Field(default=None, description="Finish reason if generation ended")


class StructuredCompletionResponse(BaseModel, Generic[T]):
    """Parsed structured response validated against a target Pydantic schema."""

    parsed: T = Field(description="Parsed Pydantic instance matching requested schema")
    raw_content: str = Field(description="Raw string output returned by LLM")
    model: str = Field(description="Model used for generation")
    provider: str = Field(description="Provider name")
    usage: UsageInfo = Field(default_factory=UsageInfo, description="Token usage details")
