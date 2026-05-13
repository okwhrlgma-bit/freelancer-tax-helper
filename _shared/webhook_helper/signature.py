"""Webhook signature 검증 (Cycle 695·LS+Polar HMAC SHA256·timing-safe)."""

from __future__ import annotations

import hashlib
import hmac


def verify_lemonsqueezy_signature(
    payload: bytes,
    signature_header: str,
    webhook_secret: str,
) -> bool:
    """LS X-Signature header HMAC SHA256 검증.

    Args:
        payload: HTTP body bytes (json.dumps 후 .encode·역직렬화 X)
        signature_header: "X-Signature" 헤더 값 (hex string)
        webhook_secret: LS Settings → Webhooks 발급된 secret

    Returns:
        bool: 일치 = True·timing-safe (hmac.compare_digest)
    """
    if not webhook_secret or not signature_header or not payload:
        return False
    try:
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
    except (AttributeError, TypeError):
        return False
    cleaned = signature_header.strip().lower()
    return hmac.compare_digest(expected, cleaned)


def verify_polar_signature(
    payload: bytes,
    signature_header: str,
    webhook_secret: str,
) -> bool:
    """Polar webhook-signature header HMAC SHA256 검증.

    Polar 표준 (https://docs.polar.sh/api-reference/webhooks-events):
        webhook-signature: t=timestamp,v1=hex_signature
        signed = f"{timestamp}.{body}"
    """
    if not webhook_secret or not signature_header or not payload:
        return False
    # Polar 형식 = "t=...,v1=..." 파싱
    parts = signature_header.strip().split(",")
    timestamp = ""
    sig = ""
    for p in parts:
        if "=" not in p:
            continue
        key, val = p.split("=", 1)
        if key.strip() == "t":
            timestamp = val.strip()
        elif key.strip() == "v1":
            sig = val.strip().lower()
    if not timestamp or not sig:
        return False
    signed_payload = f"{timestamp}.".encode() + payload
    try:
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()
    except (AttributeError, TypeError):
        return False
    return hmac.compare_digest(expected, sig)


def extract_amount_safe(value: object, default: int = 0) -> int:
    """안전한 금액 추출 (int·str·dict 모두 처리)."""
    if value is None:
        return default
    if isinstance(value, bool):
        return default  # bool은 int 파생·차단
    if isinstance(value, (int, float)):
        try:
            return int(value)
        except (ValueError, OverflowError):
            return default
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            try:
                return int(float(value))
            except ValueError:
                return default
    return default
