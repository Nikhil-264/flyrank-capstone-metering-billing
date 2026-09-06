"""
Shared helpers for reading Stripe objects, used by both the live webhook
handler (app/api/webhooks/stripe.py) and the reconciliation job
(app/services/reconciliation_service.py).
"""
from datetime import datetime, timezone
from typing import Optional


def meta_get(metadata, key: str, default=None):
    """
    Read a key from Stripe ``metadata`` whether it is a real
    ``stripe.StripeObject`` (attribute access only, no ``.get()``) or a plain
    ``dict`` (as produced by mocked Stripe objects in tests). Never call
    ``.get()`` directly on a StripeObject — see ``learnings.md``.
    """
    if metadata is None:
        return default
    if isinstance(metadata, dict):
        return metadata.get(key, default)
    return getattr(metadata, key, default)


def _raw_get(obj, key):
    val = getattr(obj, key, None)
    if val is not None:
        return val
    if isinstance(obj, dict) or hasattr(obj, "get"):
        try:
            return obj.get(key)
        except Exception:  # noqa: BLE001
            return None
    return None


def get_period_dates(sub) -> tuple[Optional[datetime], Optional[datetime]]:
    """
    Extract ``current_period_start`` / ``current_period_end`` as timezone-aware
    UTC datetimes.

    Supports both the legacy top-level location and the
    ``2025-03-31.basil``+ (Dahlia) nested ``items.data[0]`` location. If Stripe
    supplies neither, returns ``(None, None)`` — callers persist NULL and the
    quota/rollup layer falls back to the calendar month. We do **not**
    fabricate billing-period boundaries, because those feed quota windows.
    """
    start = _raw_get(sub, "current_period_start")
    end = _raw_get(sub, "current_period_end")

    if start is None:
        items = _raw_get(sub, "items")
        data = _raw_get(items, "data") if items is not None else None
        if data:
            item = data[0]
            start = _raw_get(item, "current_period_start")
            end = _raw_get(item, "current_period_end")

    start_dt = datetime.fromtimestamp(start, tz=timezone.utc) if start else None
    end_dt = datetime.fromtimestamp(end, tz=timezone.utc) if end else None
    return start_dt, end_dt
