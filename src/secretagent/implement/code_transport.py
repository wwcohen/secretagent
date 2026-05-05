"""Base64 transport for long source strings (ReAct JSON, render pipeline).

Models may use standard or URL-safe base64, optional ``b64:`` prefix, missing ``=``
padding, or accidental double-encoding; :func:`decode_transport_layers` normalizes
to UTF-8 source before write/render.
"""

from __future__ import annotations

import base64
import binascii
import re

_B64_SKIN_RE = re.compile(r'^[A-Za-z0-9+/=_-]+$')
# Short HTML still yields ~20+ char payloads; keep low enough for a second decode layer.
_MIN_B64_CHARS = 12
_MAX_LAYERS = 5


def _pad(s: str) -> str:
    return s + '=' * ((4 - len(s) % 4) % 4)


def _try_decode_one_layer(compact: str) -> bytes | None:
    padded = _pad(compact)
    try:
        out = base64.b64decode(padded, validate=False)
        if out:
            return out
    except (binascii.Error, ValueError):
        pass
    try:
        out = base64.urlsafe_b64decode(padded)
        if out:
            return out
    except (binascii.Error, ValueError):
        pass
    return None


def decode_transport_layers(s: str, *, max_layers: int = _MAX_LAYERS) -> str:
    """Strip ``b64:``; repeatedly decode base64-wrapped UTF-8 while each layer looks like base64."""
    if not isinstance(s, str) or not s.strip():
        return s
    out = s.strip()
    if out.startswith('b64:'):
        out = out[4:].lstrip()

    for _ in range(max_layers):
        compact = ''.join(out.split())
        if len(compact) < _MIN_B64_CHARS or not _B64_SKIN_RE.fullmatch(compact):
            break
        raw = _try_decode_one_layer(compact)
        if raw is None:
            break
        try:
            nxt = raw.decode('utf-8')
        except UnicodeDecodeError:
            nxt = raw.decode('utf-8', errors='replace')
        if nxt == out:
            break
        out = nxt
    return out


def encode_transport(s: str) -> str:
    """Standard base64 (UTF-8) of ``s``, no newlines (safe inside JSON strings)."""
    return base64.b64encode(s.encode('utf-8')).decode('ascii')
