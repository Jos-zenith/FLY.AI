import json
import time

import httpx
from fastapi import APIRouter, Request, Response
from opentelemetry import trace

from app.db.session import get_db
from app.services.prompt_capture import capture_prompt_log

_SENSITIVE_UPSTREAM_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "proxy-authorization",
    "x-forwarded-for",
    "x-real-ip",
}

_SENSITIVE_KEYWORD_PREFIXES = (
    "authorization",
    "cookie",
    "x-api",
    "x-auth",
    "x-secret",
    "token",
    "secret",
    "api-key",
    "session",
    "proxy-authorization",
    "forwarded",
)

router = APIRouter()

UPSTREAM_URL = "https://api.anthropic.com/v1/messages"
tracer = trace.get_tracer("ai-usage-monitor.gateway")


def _safe_upstream_headers(request_headers) -> dict[str, str]:
    safe_headers = {}
    for key, value in request_headers.items():
        lowered = key.lower()
        if lowered in {"host", "content-length"}:
            continue
        if lowered in _SENSITIVE_UPSTREAM_HEADERS:
            continue
        if any(prefix in lowered for prefix in _SENSITIVE_KEYWORD_PREFIXES):
            continue
        safe_headers[key] = value
    return safe_headers


@router.post("/gateway/v1/messages")
async def proxy_llm_call(request: Request):
    body = await request.json()
    start = time.monotonic()
    ai_asset = request.headers.get("x-ai-asset", "unknown")
    model = body.get("model")

    with tracer.start_as_current_span(
        "llm_gateway.call",
        attributes={
            "ai.asset": ai_asset,
            "llm.model": model or "unknown",
            "llm.provider": "anthropic",
        },
    ) as span:
        try:
            async with httpx.AsyncClient() as client:
                upstream_resp = await client.post(
                    UPSTREAM_URL,
                    json=body,
                    headers=_safe_upstream_headers(request.headers),
                    timeout=60.0,
                )
        except Exception as exc:
            return Response(
                content=json.dumps({"error": f"Upstream provider request failed: {exc}"}),
                status_code=502,
                media_type="application/json",
            )

        latency_ms = (time.monotonic() - start) * 1000
        prompt_text = _extract_prompt_text(body)

        try:
            resp_json = upstream_resp.json()
        except ValueError:
            resp_json = {}
        usage = resp_json.get("usage", {})

        span.set_attribute("llm.status_code", upstream_resp.status_code)
        span.set_attribute("llm.latency_ms", latency_ms)
        span.set_attribute("ai.asset", ai_asset)
        span.set_attribute("llm.prompt_length", len(prompt_text))
        span.set_attribute("llm.input_tokens", usage.get("input_tokens", 0))
        span.set_attribute("llm.output_tokens", usage.get("output_tokens", 0))

        db = next(get_db())
        try:
            capture_prompt_log(
                db,
                ai_asset=ai_asset,
                model=model,
                prompt_text=prompt_text,
                input_tokens=usage.get("input_tokens"),
                output_tokens=usage.get("output_tokens"),
                latency_ms=latency_ms,
                status=upstream_resp.status_code,
            )
        finally:
            db.close()

        if upstream_resp.status_code >= 400:
            return Response(
                content=json.dumps({"error": "Upstream provider returned an error response."}),
                status_code=502,
                media_type="application/json",
            )

        return Response(
            content=upstream_resp.content,
            status_code=upstream_resp.status_code,
            media_type="application/json",
        )


def _extract_prompt_text(body: dict) -> str:
    messages = body.get("messages", [])
    parts = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            parts.extend(item.get("text", "") for item in content if isinstance(item, dict))
    return "\n".join(parts)
