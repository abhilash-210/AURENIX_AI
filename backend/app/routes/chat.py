"""
Chat completion endpoint route handler.

Exposes POST /api/v1/chat with support for standard JSON completions
and Server-Sent Events (SSE) streaming.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse, ChatResponseData
from app.schemas.common import ResponseMeta
from app.services.llm.service import LLMService
from app.services.llm.types import CompletionOptions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


def get_llm_service() -> LLMService:
    """Dependency provider for LLMService instance."""
    return LLMService()


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ChatResponse,
    summary="Execute LLM chat completion",
    description="Send messages to the provider-agnostic LLM Gateway. Supports JSON responses and SSE streaming.",
)
async def chat_completion(
    payload: ChatRequest,
    request: Request,
    llm_service: LLMService = Depends(get_llm_service),
) -> ChatResponse | StreamingResponse:
    """
    Handle chat completion requests.

    If payload.stream is True, returns an SSE stream (text/event-stream).
    Otherwise, returns standard ChatResponse JSON envelope.
    """
    request_id: str = getattr(request.state, "request_id", "unknown")

    options = CompletionOptions(
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        top_p=payload.top_p,
    )

    if payload.stream:

        async def sse_generator() -> AsyncGenerator[str, None]:
            try:
                async for chunk in llm_service.stream_complete(
                    messages=payload.messages,
                    options=options,
                    provider_name=payload.provider,
                ):
                    chunk_data = {
                        "delta": chunk.delta,
                        "finish_reason": chunk.finish_reason,
                    }
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as exc:
                logger.exception("Error during LLM token streaming", extra={"request_id": request_id})
                err_payload = {"error": str(exc), "code": getattr(exc, "error_code", "LLM_ERROR")}
                yield f"data: {json.dumps(err_payload)}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id,
            },
        )

    # Standard non-streaming completion
    res = await llm_service.complete(
        messages=payload.messages,
        options=options,
        provider_name=payload.provider,
    )

    return ChatResponse(
        data=ChatResponseData(
            content=res.content,
            role=res.role,
            model=res.model,
            provider=res.provider,
            usage=res.usage,
            finish_reason=res.finish_reason,
        ),
        meta=ResponseMeta(request_id=request_id),
    )
