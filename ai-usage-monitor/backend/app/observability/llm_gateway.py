import time

import httpx
from fastapi import APIRouter, Request, Response

from app.db.session import get_db
from app.models import PromptLog
from app.services.pii import redact

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

    sanitized_prompt, pii_counts = redact(prompt_text)

    db = next(get_db())
    db.add(
        PromptLog(
            ai_asset=request.headers.get("x-ai-asset", "unknown"),
            model=model,
            sanitized_prompt=sanitized_prompt,
            pii_detected=pii_counts,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            latency_ms=latency_ms,
            status=upstream_resp.status_code,
        )
    )
    db.commit()

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
