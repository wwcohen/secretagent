"""ReAct helpers used only when ``vlm.enabled`` / ``react.use_vlm`` is on."""

from __future__ import annotations

import inspect
import json
import re
from typing import Any, Callable

from secretagent.implement.code_transport import decode_transport_layers

_JSON_B64_FIELDS = ('code', 'current_code')


def truncate_at_observation(text: str) -> str:
    m = re.search(r'\nObservation\s*:', text)
    if m:
        return text[: m.start()]
    return text


def parse_thought(text: str) -> str | None:
    m = re.search(
        r'Thought\s*:\s*(.*?)(?=\n(?:Action|Final Answer)\s*:|\Z)',
        text,
        re.DOTALL,
    )
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


def parse_final_answer(text: str) -> str | None:
    m = re.search(r'Final Answer\s*:\s*(.*)', text, re.DOTALL)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


def parse_action_last(text: str) -> tuple[str | None, str | None]:
    last: tuple[str, str] | None = None
    for action_m in re.finditer(r'Action\s*:\s*(.+?)(?:\n|$)', text):
        tool_name = action_m.group(1).strip()
        tail = text[action_m.end() :]
        input_m = re.search(
            r'Action\s+Input\s*:\s*(.*?)(?=\n(?:Observation|Thought|Action|Final Answer)\s*:|\Z)',
            tail,
            re.DOTALL,
        )
        action_input = input_m.group(1).strip() if input_m else ''
        last = (tool_name, action_input)
    if last is None:
        return None, None
    return last


def parse_react_vlm_step(response: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Thought / Final Answer from truncated text; tool from full text (last Action wins)."""
    prefixed = f'Thought: {response}'
    truncated = truncate_at_observation(prefixed)
    return (
        parse_thought(truncated),
        parse_final_answer(truncated),
        *parse_action_last(prefixed),
    )


def decode_tool_b64(s: str) -> str:
    """Undo base64 transport for ``code`` / ``current_code`` tool JSON fields."""
    return decode_transport_layers(s)


def leading_json_object(arg_str: str) -> dict[str, Any] | None:
    s = arg_str.lstrip()
    i = s.find('{')
    if i < 0:
        return None
    try:
        obj, _end = json.JSONDecoder().raw_decode(s, i)
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _fill_missing_tool_json_payload(payload: dict[str, Any], fn: Callable[..., Any]) -> dict[str, Any]:
    """VLMs often omit ``framework`` when only base64 ``code`` is sent; use run config when possible."""
    from secretagent import config

    out = dict(payload)
    name = getattr(fn, '__name__', '')
    fw = config.get('benchmark.output_framework') or config.get('dataset.framework')

    if name == 'render_generated_image' and 'code' in out and 'framework' not in out and fw is not None:
        out['framework'] = str(fw)
    if name == 'fix_code_from_rendered_and_reference':
        if 'framework' not in out and fw is not None:
            out['framework'] = str(fw)
        out.setdefault('reference_screenshot', '')
        out.setdefault('generated_screenshot', '')
    return out


def coerce_react_tool_input(
    fn: Callable[..., Any],
    arg_str: str,
    react_images: dict | None = None,
) -> Any:
    """JSON Action Input (with optional trailing junk), base64 ``code``/``current_code``, ``follow_wrapped``."""
    sig = inspect.signature(fn, follow_wrapped=True)
    params = list(sig.parameters.values())
    accepts_react_images = 'react_images' in sig.parameters
    call_kw = {'react_images': react_images} if accepts_react_images else {}
    typed_params = [p for p in params if p.name != 'react_images']

    if not typed_params:
        return fn(**call_kw)

    if len(typed_params) >= 2:
        payload = leading_json_object(arg_str)
        if isinstance(payload, dict):
            payload = _fill_missing_tool_json_payload(payload, fn)
            names = [p.name for p in typed_params]
            if all(n in payload for n in names):
                coerced_kw: dict[str, Any] = {}
                for p in typed_params:
                    val = payload[p.name]
                    ann = p.annotation
                    if ann is inspect.Parameter.empty or ann is str:
                        coerced_kw[p.name] = val if isinstance(val, str) else str(val)
                    else:
                        try:
                            coerced_kw[p.name] = ann(val)
                        except (TypeError, ValueError):
                            coerced_kw[p.name] = val
                for k in _JSON_B64_FIELDS:
                    if k in coerced_kw and isinstance(coerced_kw[k], str):
                        coerced_kw[k] = decode_tool_b64(coerced_kw[k])
                return fn(**coerced_kw, **call_kw)

    if len(typed_params) == 1:
        ann = typed_params[0].annotation
        if ann is inspect.Parameter.empty or ann is str:
            return fn(arg_str, **call_kw)
        try:
            return fn(ann(arg_str), **call_kw)
        except (ValueError, TypeError):
            return fn(arg_str, **call_kw)

    parts = [p.strip() for p in re.split(r'[|,]', arg_str)]
    coerced = []
    for part, param in zip(parts, typed_params):
        ann = param.annotation
        if ann is inspect.Parameter.empty or ann is str:
            coerced.append(part)
        else:
            try:
                coerced.append(ann(part))
            except (ValueError, TypeError):
                coerced.append(part)
    return fn(*coerced, **call_kw)
