import json
import logging
from collections.abc import Generator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

THINK_OPEN = "<think>"
THINK_CLOSE = "</think>"


def _split_safe(buffer: str) -> tuple[str, str]:
    idx = buffer.rfind("<")
    if idx == -1:
        return buffer, ""
    trailing = buffer[idx:]
    if THINK_OPEN.startswith(trailing) or THINK_CLOSE.startswith(trailing):
        return buffer[:idx], trailing
    return buffer, ""


def stream_chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float = 0.7,
) -> Generator[str, None, None]:
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {
        "model": model or settings.ollama_model,
        "messages": messages,
        "stream": True,
        "think": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens or settings.ollama_max_tokens,
        },
    }

    in_think = False
    buffer = ""

    with httpx.Client(timeout=120.0) as client:
        with client.stream("POST", url, json=payload) as response:
            if response.status_code == 404:
                raise ValueError(f"Model '{payload['model']}' not found in Ollama")
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                if chunk.get("done"):
                    break
                token = chunk.get("message", {}).get("content", "")
                if not token:
                    continue

                buffer += token

                while True:
                    if in_think:
                        end = buffer.find(THINK_CLOSE)
                        if end == -1:
                            buffer = ""
                            break
                        in_think = False
                        buffer = buffer[end + len(THINK_CLOSE) :]
                    else:
                        start = buffer.find(THINK_OPEN)
                        if start == -1:
                            safe, buffer = _split_safe(buffer)
                            if safe:
                                yield safe
                            break
                        if start > 0:
                            yield buffer[:start]
                        in_think = True
                        buffer = buffer[start + len(THINK_OPEN) :]

    if buffer and not in_think:
        yield buffer
