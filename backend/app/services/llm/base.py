"""
Abstract base class definition for LLM providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, TypeVar
from pydantic import BaseModel

from app.services.llm.types import (
    ChatCompletionChunk,
    ChatCompletionResponse,
    ChatMessage,
    CompletionOptions,
    StructuredCompletionResponse,
)

T = TypeVar("T", bound=BaseModel)


class BaseLLMProvider(ABC):
    """
    Abstract interface that all LLM provider implementations must satisfy.

    Decouples application logic from provider-specific REST endpoints, SDKs,
    and payload formats.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return unique provider identifier (e.g. 'openai', 'anthropic', 'mock')."""
        ...

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> ChatCompletionResponse:
        """
        Execute a standard chat completion request.

        Args:
            messages: List of conversation turn messages.
            options: Completion hyper-parameters.

        Returns:
            ChatCompletionResponse containing text output and metadata.
        """
        ...

    @abstractmethod
    async def complete_structured(
        self,
        messages: list[ChatMessage],
        response_schema: type[T],
        options: CompletionOptions,
    ) -> StructuredCompletionResponse[T]:
        """
        Execute a chat completion request and parse output into target Pydantic model.

        Args:
            messages: List of conversation turn messages.
            response_schema: Pydantic model class to validate output against.
            options: Completion hyper-parameters.

        Returns:
            StructuredCompletionResponse containing parsed instance and metadata.
        """
        ...

    @abstractmethod
    async def stream_complete(
        self,
        messages: list[ChatMessage],
        options: CompletionOptions,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        """
        Stream chat completion tokens asynchronously.

        Args:
            messages: List of conversation turn messages.
            options: Completion hyper-parameters.

        Yields:
            ChatCompletionChunk deltas as they are received from provider.
        """
        ...
