"""Webhook 이벤트 분류·payload 파싱 (Cycle 695·697·LS+Polar+PortOne 통합).

Cycle 1232 갱신: 환율 1400 하드코딩 → constants.RATE_USD_KRW (env var) 분리.
"""

from __future__ import annotations

from dataclasses import dataclass

from constants import RATE_USD_KRW


@dataclass(frozen=True)
class WebhookEvent:
    """Webhook 이벤트 통합 표현 (PG 무관)."""

    provider: str  # "lemonsqueezy"·"polar"·"portone"
    event_type: str  # 원본 PG 이벤트 이름
    category: str  # 분류 (paid·refund·failed·license·other)
    is_test: bool  # 테스트 이벤트 여부
    customer_email: str
    amount_krw: int  # 한국 환산 (USD * 1400 또는 KRW 직접)
    raw: dict  # 원본 payload


# 통합 카테고리 매핑
WEBHOOK_EVENT_CATEGORY: dict[str, dict[str, str]] = {
    "lemonsqueezy": {
        "order_created": "paid",
        "subscription_created": "paid",
        "subscription_payment_success": "paid",
        "subscription_payment_recovered": "paid",
        "subscription_resumed": "paid",
        "subscription_unpaused": "paid",
        "order_refunded": "refund",
        "subscription_cancelled": "refund",
        "subscription_expired": "refund",
        "subscription_paused": "refund",
        "subscription_payment_failed": "failed",
        "subscription_updated": "other",
        "license_key_created": "license",
        "license_key_updated": "license",
    },
    "polar": {
        "checkout.created": "other",
        "checkout.updated": "other",
        "order.created": "paid",
        "order.refunded": "refund",
        "subscription.created": "paid",
        "subscription.updated": "other",
        "subscription.canceled": "refund",
        "subscription.uncanceled": "paid",
        "subscription.revoked": "refund",
        "benefit.created": "other",
        "benefit_grant.created": "license",
        "benefit_grant.updated": "license",
        "benefit_grant.revoked": "refund",
        "product.created": "other",
        "product.updated": "other",
        "refund.created": "refund",
    },
    "portone": {
        "Transaction.Paid": "paid",
        "Transaction.PartialCancelled": "refund",
        "Transaction.Cancelled": "refund",
        "Transaction.Failed": "failed",
        "Transaction.Ready": "other",
        "Transaction.VirtualAccountIssued": "other",
    },
}


def classify_lemonsqueezy_event(event_name: str) -> str:
    """LS event_name → 분류 (paid·refund·failed·license·other)."""
    if not event_name or not isinstance(event_name, str):
        return "other"
    return WEBHOOK_EVENT_CATEGORY["lemonsqueezy"].get(event_name.strip(), "other")


def classify_polar_event(event_type: str) -> str:
    """Polar event type → 분류."""
    if not event_type or not isinstance(event_type, str):
        return "other"
    return WEBHOOK_EVENT_CATEGORY["polar"].get(event_type.strip(), "other")


def classify_portone_event(event_type: str) -> str:
    """PortOne event type → 분류."""
    if not event_type or not isinstance(event_type, str):
        return "other"
    return WEBHOOK_EVENT_CATEGORY["portone"].get(event_type.strip(), "other")


def is_test_event(payload: dict, provider: str = "") -> bool:
    """테스트 이벤트 여부 (운영 X·로그만)."""
    if not isinstance(payload, dict):
        return False
    # PG별 테스트 표식
    if provider == "lemonsqueezy":
        meta = payload.get("meta", {})
        return bool(meta.get("test_mode", False))
    if provider == "polar":
        # Polar = data.attributes.test 없음·sandbox 환경 = 다른 base_url
        return bool(payload.get("test_mode", False))
    if provider == "portone":
        return bool(payload.get("isTest", False)) or "test_" in str(
            payload.get("imp_uid", "")
        )
    # 자동 추론 (provider 미지정)
    s = str(payload).lower()
    return "test_mode" in s or '"test"' in s or "sandbox" in s


def extract_payment_amount(payload: dict, provider: str = "") -> int:
    """결제 금액 추출 (한국 KRW 환산·정수)."""
    if not isinstance(payload, dict):
        return 0

    if provider == "lemonsqueezy":
        # data.attributes.total = 센트 (USD)
        attrs = payload.get("data", {}).get("attributes", {})
        total_cents = attrs.get("total", 0) or attrs.get("total_usd", 0)
        try:
            return int(int(total_cents) / 100 * RATE_USD_KRW)  # USD → KRW (env)
        except (ValueError, TypeError):
            return 0

    if provider == "polar":
        # data.attributes.amount = 센트 (USD 기본)
        data = payload.get("data", {})
        amount = data.get("amount", 0) or data.get("net_amount", 0)
        try:
            return int(int(amount) / 100 * RATE_USD_KRW)
        except (ValueError, TypeError):
            return 0

    if provider == "portone":
        # PortOne v2 = amount_paid (KRW 직접)
        amount = payload.get("amount", {})
        if isinstance(amount, dict):
            return int(amount.get("total", 0) or amount.get("paid", 0))
        try:
            return int(amount)
        except (ValueError, TypeError):
            return 0

    return 0


def parse_webhook_payload(
    payload: dict,
    provider: str,
) -> WebhookEvent:
    """webhook payload → WebhookEvent 통합 표현."""
    if not isinstance(payload, dict):
        msg = "payload = dict 의무"
        raise ValueError(msg)
    if provider not in {"lemonsqueezy", "polar", "portone"}:
        msg = "provider = lemonsqueezy·polar·portone 의무"
        raise ValueError(msg)

    # 이벤트 이름 추출
    event_name = ""
    if provider == "lemonsqueezy":
        event_name = payload.get("meta", {}).get("event_name", "")
    elif provider == "polar" or provider == "portone":
        event_name = payload.get("type", "")

    # 분류
    classifier = {
        "lemonsqueezy": classify_lemonsqueezy_event,
        "polar": classify_polar_event,
        "portone": classify_portone_event,
    }[provider]
    category = classifier(event_name)

    # customer email
    email = ""
    if provider == "lemonsqueezy":
        attrs = payload.get("data", {}).get("attributes", {})
        email = attrs.get("user_email", "") or attrs.get("customer_email", "")
    elif provider == "polar":
        email = payload.get("data", {}).get("customer_email", "") or payload.get(
            "data", {}
        ).get("user", {}).get("email", "")
    elif provider == "portone":
        email = payload.get("buyer_email", "")

    return WebhookEvent(
        provider=provider,
        event_type=event_name,
        category=category,
        is_test=is_test_event(payload, provider),
        customer_email=str(email or ""),
        amount_krw=extract_payment_amount(payload, provider),
        raw=payload,
    )
