"""FastAPI route handlers."""

import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger

from config.settings import Settings
from providers.common import get_user_facing_error_message
from providers.exceptions import InvalidRequestError, ProviderError

from .dependencies import get_provider_for_type, get_settings
from .models.anthropic import MessagesRequest, TokenCountRequest
from .models.responses import TokenCountResponse
from .optimization_handlers import try_optimizations
from .request_utils import get_token_count

router = APIRouter()


# =============================================================================
# Routes
# =============================================================================
@router.post("/v1/messages")
async def create_message(
    request_data: MessagesRequest,
    raw_request: Request,
    settings: Settings = Depends(get_settings),
):
    """Create a message (always streaming)."""

    try:
        if not request_data.messages:
            raise InvalidRequestError("messages cannot be empty")

        optimized = try_optimizations(request_data, settings)
        if optimized is not None:
            return optimized
        logger.debug("No optimization matched, routing to provider")

        # Resolve provider from the model-aware mapping
        provider_type = Settings.parse_provider_type(
            request_data.resolved_provider_model or settings.model
        )
        provider = get_provider_for_type(provider_type)

        request_id = f"req_{uuid.uuid4().hex[:12]}"
        logger.info(
            "API_REQUEST: request_id={} model={} messages={}",
            request_id,
            request_data.model,
            len(request_data.messages),
        )
        logger.debug("FULL_PAYLOAD [{}]: {}", request_id, request_data.model_dump())

        input_tokens = get_token_count(
            request_data.messages, request_data.system, request_data.tools
        )
        return StreamingResponse(
            provider.stream_response(
                request_data,
                input_tokens=input_tokens,
                request_id=request_id,
            ),
            media_type="text/event-stream",
            headers={
                "X-Accel-Buffering": "no",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    except ProviderError:
        raise
    except Exception as e:
        logger.error(f"Error: {e!s}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=getattr(e, "status_code", 500),
            detail=get_user_facing_error_message(e),
        ) from e


@router.post("/v1/messages/count_tokens")
async def count_tokens(request_data: TokenCountRequest):
    """Count tokens for a request."""
    request_id = f"req_{uuid.uuid4().hex[:12]}"
    with logger.contextualize(request_id=request_id):
        try:
            tokens = get_token_count(
                request_data.messages, request_data.system, request_data.tools
            )
            logger.info(
                "COUNT_TOKENS: request_id={} model={} messages={} input_tokens={}",
                request_id,
                getattr(request_data, "model", "unknown"),
                len(request_data.messages),
                tokens,
            )
            return TokenCountResponse(input_tokens=tokens)
        except Exception as e:
            logger.error(
                "COUNT_TOKENS_ERROR: request_id={} error={}\n{}",
                request_id,
                get_user_facing_error_message(e),
                traceback.format_exc(),
            )
            raise HTTPException(
                status_code=500, detail=get_user_facing_error_message(e)
            ) from e


@router.get("/")
async def root(settings: Settings = Depends(get_settings)):
    """Root endpoint."""
    return {
        "status": "ok",
        "provider": settings.provider_type,
        "model": settings.model,
    }


@router.get("/v1/models")
async def list_models():
    """List available models (required by Claude Code)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "claude-opus-4-6",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
            {
                "id": "claude-sonnet-4-6",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
            {
                "id": "claude-haiku-4-5",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
            {
                "id": "claude-3-opus",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
            {
                "id": "claude-3-5-sonnet-20241022",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
            {
                "id": "claude-3-5-sonnet",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
            {
                "id": "claude-3-5-haiku-20241022",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
            {
                "id": "claude-3-haiku",
                "object": "model",
                "created": 1709596800,
                "owned_by": "anthropic",
            },
        ],
    }


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Auth endpoints for Claude Code v2.1.119+ compatibility
@router.get("/v1/organizations")
async def organizations():
    return [{"id": "org_ragspro", "name": "RAGSPRO", "role": "owner"}]


@router.get("/v1/account")
async def account():
    return {
        "id": "usr_ragspro",
        "email": "ragsproai@gmail.com",
        "name": "Raghav Shah",
        "plan": "pro",
        "organization": {"id": "org_ragspro", "name": "RAGSPRO"},
    }


@router.post("/v1/auth/token")
async def auth_token():
    return {"access_token": "freecc", "token_type": "bearer", "expires_in": 86400}


@router.get("/v1/auth/session")
async def auth_session():
    return {"authenticated": True, "user_id": "usr_ragspro", "plan": "pro"}


@router.post("/v1/organizations/{org_id}/api_keys")
async def create_api_key(org_id: str):
    return {"api_key": "freecc", "name": "ragscode"}


@router.get("/v1/organizations/{org_id}/api_keys")
async def list_api_keys(org_id: str):
    return {"data": [{"id": "key_1", "name": "ragscode", "api_key": "freecc"}]}


@router.post("/v1/messages/batches")
async def message_batches():
    return {"id": "batch_1", "status": "completed"}


@router.get("/api/auth/session")
async def api_auth_session():
    return {"authenticated": True, "user_id": "usr_ragspro"}


@router.get("/api/account")
async def api_account():
    return {"id": "usr_ragspro", "email": "ragsproai@gmail.com", "plan": "pro"}


@router.get("/api/billing")
async def api_billing():
    return {
        "plan": "pro",
        "status": "active",
        "usage": {"tokens": 0, "limit": 999999999},
    }


@router.post("/stop")
async def stop_cli(request: Request):
    """Stop all CLI sessions and pending tasks."""
    handler = getattr(request.app.state, "message_handler", None)
    if not handler:
        # Fallback if messaging not initialized
        cli_manager = getattr(request.app.state, "cli_manager", None)
        if cli_manager:
            await cli_manager.stop_all()
            logger.info("STOP_CLI: source=cli_manager cancelled_count=N/A")
            return {"status": "stopped", "source": "cli_manager"}
        raise HTTPException(status_code=503, detail="Messaging system not initialized")

    count = await handler.stop_all_tasks()
    logger.info("STOP_CLI: source=handler cancelled_count={}", count)
    return {"status": "stopped", "cancelled_count": count}
