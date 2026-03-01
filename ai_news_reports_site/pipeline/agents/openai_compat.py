from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class OpenAIChatResult:
    """Normalized result from the OpenAI SDK (chat.completions)."""

    model: str
    text: str


def _strip_code_fences(text: str) -> str:
    """Remove ```json ...``` wrappers if present."""

    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    return t.strip()


def _extract_json_object(text: str) -> Optional[str]:
    """Best-effort JSON object extraction from messy model output."""

    raw = _strip_code_fences(text)
    if not raw:
        return None

    if raw.startswith("{") and raw.endswith("}"):
        return raw

    start = raw.find("{")
    if start == -1:
        return None

    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(raw)):
        ch = raw[i]

        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1].strip()

    return None


def sanitize_model_name(model: Optional[str]) -> Optional[str]:
    if model is None:
        return None
    m = str(model).strip()
    return m or None


def sanitize_model_list(models: Sequence[str] | None) -> List[str]:
    out: List[str] = []
    for m in (models or []):
        sm = sanitize_model_name(m)
        if sm and sm not in out:
            out.append(sm)
    return out


def chat_completion_text(
    *,
    client: Any,
    model: str,
    system: str,
    user: str,
    fallback_models: Sequence[str] | None = None,
    temperature: float = 0.2,
) -> OpenAIChatResult:
    """Plain text generation via chat.completions, with optional model fallbacks."""

    models = sanitize_model_list([model, *list(fallback_models or [])])
    last_err: Exception | None = None

    for m in models:
        try:
            completion = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=temperature,
            )
            text = (completion.choices[0].message.content or "").strip()
            return OpenAIChatResult(model=m, text=text)
        except Exception as e:
            last_err = e
            continue

    raise last_err or RuntimeError("OpenAI call failed")


def chat_completion_json(
    *,
    client: Any,
    model: str,
    system: str,
    user: str,
    schema_name: str,
    schema: Dict[str, Any] | None,
    strict: bool = True,
    fallback_models: Sequence[str] | None = None,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """JSON generation via chat.completions.

    - Tries Structured Outputs (json_schema) when a schema is provided.
    - Falls back to JSON mode (json_object) if schema isn't supported.
    - If the SDK doesn't support response_format, falls back to prompt-only JSON.
    - Tries fallback models if the primary model is unavailable.
    """

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]

    models = sanitize_model_list([model, *list(fallback_models or [])])
    last_err: Exception | None = None

    for m in models:
        if schema is not None:
            try:
                try:
                    completion = client.chat.completions.create(
                        model=m,
                        messages=messages,
                        temperature=temperature,
                        response_format={
                            "type": "json_schema",
                            "json_schema": {
                                "name": schema_name,
                                "schema": schema,
                                "strict": bool(strict),
                            },
                        },
                    )
                except TypeError as te:
                    # Older SDKs may not support response_format; fall back to prompt-only JSON.
                    if "response_format" in str(te):
                        completion = client.chat.completions.create(
                            model=m,
                            messages=messages,
                            temperature=temperature,
                        )
                    else:
                        raise

                raw = _strip_code_fences(completion.choices[0].message.content or "")
                blob = _extract_json_object(raw) or raw
                return json.loads(blob)
            except Exception as e:
                last_err = e

        try:
            try:
                completion = client.chat.completions.create(
                    model=m,
                    messages=messages,
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
            except TypeError as te:
                if "response_format" in str(te):
                    completion = client.chat.completions.create(
                        model=m,
                        messages=messages,
                        temperature=temperature,
                    )
                else:
                    raise

            raw = completion.choices[0].message.content or ""
            blob = _extract_json_object(raw)
            if not blob:
                raise ValueError("Model did not return a JSON object")
            return json.loads(blob)
        except Exception as e:
            last_err = e
            continue

    raise last_err or RuntimeError("OpenAI call failed")
