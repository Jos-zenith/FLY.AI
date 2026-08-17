import time

import httpx
from fastapi import APIRouter, Request, Response

from app.db.session import get_db
from app.services.prompt_capture import capture_prompt_log

router = APIRouter()

UPSTREAM_URL = "https://api.anthropic.com/v1/messages"


@router.post("/gateway/v1/messages")
async def proxy_llm_call(request: Request):
    body = await request.json()
    start = time.monotonic()

    async with httpx.AsyncClient() as client:
        upstream_resp = await client.post(
            UPSTREAM_URL,
            json=body,
            headers={k: v for k, v in request.headers.items() if k.lower() != "host"},
            timeout=60.0,
        )
    latency_ms = (time.monotonic() - start) * 1000

    prompt_text = _extract_prompt_text(body)
    model = body.get("model")
    resp_json = upstream_resp.json()
    usage = resp_json.get("usage", {})

    db = next(get_db())
    capture_prompt_log(
        db,
        ai_asset=request.headers.get("x-ai-asset", "unknown"),
        model=model,
        prompt_text=prompt_text,
        input_tokens=usage.get("input_tokens"),
        output_tokens=usage.get("output_tokens"),
        latency_ms=latency_ms,
        status=upstream_resp.status_code,
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
