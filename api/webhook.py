"""freelancer-tax-helper webhook 진입점 (Agent G·Cycle 1362·signature 검증).

PO 명령 일괄 3 정합:
- HMAC-SHA256 검증 (PortOne 또는 Polar webhook_secret)
- 실패 시 401 응답
- 성공 시 license_key 발급 + DB 저장 (실 운영 = DB·현재는 logging)
- 헌법 §3 정합 (.env only·하드코딩 X)·timeout=10·UTF-8

사용법 (FastAPI 가정·실 배포 시 활성):
    from fastapi import FastAPI, Request
    from api.webhook import webhook_handler
    app = FastAPI()
    app.post("/api/webhook")(webhook_handler)

또는 Streamlit·Vercel Functions·기타 진입점 = handle_webhook_payload() 직접 호출.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

# _shared 경로 등록 (Cycle 168 분리·local sub-package 정합)
SHARED_PATH = Path(__file__).parent.parent / "_shared"
if SHARED_PATH.exists() and str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WebhookResult:
    """Webhook 처리 결과."""

    status_code: int  # 200 또는 401
    body: dict
    license_key: str = ""  # 성공 시 발급된 라이선스


def _try_verify_polar(payload: bytes, signature: str, secret: str) -> bool:
    """Polar webhook 시그니처 검증 (timing-safe)."""
    try:
        from webhook_helper.signature import verify_polar_signature
        return verify_polar_signature(payload, signature, secret)
    except ImportError:
        return False


def _try_verify_portone(payload: bytes, signature: str, secret: str) -> bool:
    """PortOne webhook 시그니처 검증 (timing-safe·SHA256 hex)."""
    try:
        from payments import verify_webhook_signature
        return verify_webhook_signature(payload, signature, secret)
    except ImportError:
        return False


def _issue_license_key(prefix: str = "FRL") -> str:
    """라이선스 키 발급 (실 운영 = DB unique 제약·현재 = generate_receipt_id)."""
    try:
        from payments import generate_receipt_id
        return generate_receipt_id(prefix=prefix)
    except ImportError:
        # 폴백 = secrets.token_hex
        import secrets
        ts = datetime.now(UTC).strftime("%Y%m%d")
        return f"{prefix}-{ts}-{secrets.token_hex(4).upper()}"


def handle_webhook_payload(
    payload: bytes,
    signature_header: str,
    provider: str = "polar",
) -> WebhookResult:
    """Webhook payload 처리 핵심 (FastAPI·Vercel·Streamlit 공통 entry).

    Args:
        payload: HTTP body bytes (json.dumps 후 .encode·역직렬화 X)
        signature_header: PG 발급 시그니처 헤더
        provider: "polar" 또는 "portone" (env PAYMENT_PROVIDER 우선)

    Returns:
        WebhookResult: 401 = invalid·200 = 발급 + 저장 완료

    Note:
        실 운영 = license_key를 DB에 저장 + 이메일 발송 (resend_email_helper).
        현재는 logging만·PO 결정 후 활성.
    """
    secret = ""
    verified = False
    provider_used = provider.lower()

    polar_secret = os.environ.get("POLAR_WEBHOOK_SECRET", "")
    portone_secret = os.environ.get("PORTONE_WEBHOOK_SECRET", "")

    # 우선 provider별 secret 시도·env 동시 설정 시 둘 다 시도
    if provider_used == "polar" and polar_secret:
        secret = polar_secret
        verified = _try_verify_polar(payload, signature_header, secret)
    elif provider_used == "portone" and portone_secret:
        secret = portone_secret
        verified = _try_verify_portone(payload, signature_header, secret)
    else:
        # provider 미지정·env 둘 다 시도
        if polar_secret:
            verified = _try_verify_polar(payload, signature_header, polar_secret)
            if verified:
                provider_used = "polar"
        if not verified and portone_secret:
            verified = _try_verify_portone(payload, signature_header, portone_secret)
            if verified:
                provider_used = "portone"

    if not verified:
        logger.warning("Webhook 시그니처 검증 실패 (provider=%s)", provider_used)
        return WebhookResult(
            status_code=401,
            body={"error": "invalid signature", "provider": provider_used},
        )

    # 시그니처 OK·payload 파싱
    try:
        event = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.warning("Webhook payload 파싱 실패: %s", e)
        return WebhookResult(
            status_code=400,
            body={"error": "invalid payload"},
        )

    # license_key 발급 (실 운영 = DB 저장·이메일 발송)
    license_key = _issue_license_key(prefix="FRL")
    event_type = (
        event.get("type")
        or event.get("event_name")
        or event.get("event_type")
        or "unknown"
    )
    logger.info(
        "Webhook 성공·provider=%s·event=%s·license=%s",
        provider_used, event_type, license_key,
    )

    return WebhookResult(
        status_code=200,
        body={
            "ok": True,
            "license_key": license_key,
            "event_type": event_type,
            "provider": provider_used,
        },
        license_key=license_key,
    )


# FastAPI·Starlette 호환 핸들러 (실 배포 시 활성)
async def webhook_handler(request):  # noqa: ANN001 (FastAPI Request·optional dep)
    """FastAPI·Starlette 호환 async 핸들러.

    실 배포 시 사용 (FastAPI 설치 후):
        from api.webhook import webhook_handler
        app.post("/api/webhook")(webhook_handler)
    """
    payload = await request.body()
    sig = (
        request.headers.get("webhook-signature")
        or request.headers.get("x-portone-signature")
        or request.headers.get("X-Signature")
        or ""
    )
    provider = request.headers.get("X-Provider", "polar")
    result = handle_webhook_payload(payload, sig, provider=provider)
    return {"status_code": result.status_code, **result.body}


__all__ = ["WebhookResult", "handle_webhook_payload", "webhook_handler"]
