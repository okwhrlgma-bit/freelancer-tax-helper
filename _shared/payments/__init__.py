"""30-apps 공유 결제 wrapper template (PortOne v2·Stripe·Lemon Squeezy 3 옵션).

ADR 0058 정합·캐시카우 검증 통과 시 배포 허용·헌법 §3 정합 (API 키 .env only).
사용처: #31·#32·향후 캐시카우 통과 앱 모두.

원칙:
- API 키 = .env only (헌법 §3·하드코딩 X)
- timeout = 10 (헌법 §3·외부 API)
- 영수증 = 사용자 컴퓨터 + 클라우드 백업 옵션
- BYOK 옵션 = 사용자 본인 PG 키 직접 사용 가능

본 모듈 = template scaffold·실 결제 처리는 각 앱이 사업자 등록 후 활성.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class PaymentProvider(StrEnum):
    """결제 제공자 (3 옵션)."""

    PORTONE = "portone"  # 한국 PG·세금계산서 자동·체크카드
    STRIPE = "stripe"  # 글로벌·2.9% + $0.30·VAT 직접
    LEMON_SQUEEZY = "lemonsqueezy"  # 글로벌 MoR·5% + $0.50·VAT 위임


@dataclass(frozen=True)
class PaymentConfig:
    """결제 설정 (env from .env)."""

    provider: str
    api_key: str
    secret_key: str
    webhook_secret: str
    timeout_sec: int = 10  # 헌법 §3 정합
    sandbox: bool = True

    @classmethod
    def from_env(cls, provider: str) -> PaymentConfig:
        """env에서 자동 로드 (하드코딩 X·헌법 §3 정합)."""
        prefix = provider.upper()
        return cls(
            provider=provider,
            api_key=os.environ.get(f"{prefix}_API_KEY", ""),
            secret_key=os.environ.get(f"{prefix}_SECRET_KEY", ""),
            webhook_secret=os.environ.get(f"{prefix}_WEBHOOK_SECRET", ""),
            sandbox=os.environ.get(f"{prefix}_SANDBOX", "true").lower() == "true",
        )

    def is_configured(self) -> bool:
        """필수 키 모두 존재 여부."""
        return bool(self.api_key and self.secret_key)


@dataclass(frozen=True)
class CheckoutItem:
    """결제 항목 (3 PG 공통)."""

    name: str  # 상품명
    amount_krw: int  # 원 단위
    currency: str = "KRW"
    interval: str = "monthly"  # monthly·yearly·one-time
    description: str = ""


def select_provider(country: str = "KR") -> PaymentProvider:
    """국가별 권장 PG 자동 선택.

    - KR: PortOne (한국 카드·세금계산서·국내 사용자)
    - 글로벌·EU: LemonSqueezy (MoR·VAT 위임)
    - US: Stripe (최저 수수료·but VAT 직접)
    """
    country_upper = country.upper()
    if country_upper == "KR":
        return PaymentProvider.PORTONE
    if country_upper in {"US", "CA"}:
        return PaymentProvider.STRIPE
    return PaymentProvider.LEMON_SQUEEZY


# 가격 권장 (벤치마크 정합)
PRICE_BENCHMARKS_KRW: dict[str, int] = {
    "freelancer-tax-helper": 9_900,  # 삼쩜삼 정액 변형
    "sidehustle-tracker": 4_900,  # Habit Pixel 패턴 ($5)
    "kdc-classify": 4_900,  # niche·작은 시장
    "librarian-overtime": 4_900,  # 사서 자비 한도 정합
}


# PG 수수료 (PortOne v2·2026 기준·sandbox/production 동일)
# 출처: https://portone.io/korea/ko/docs/ko/pricing
PG_FEE_PERCENT: dict[PaymentProvider, float] = {
    PaymentProvider.PORTONE: 3.3,  # 한국 카드 평균 (2.5~3.5% 범위 중앙값)
    PaymentProvider.STRIPE: 2.9,  # 미국·EU 표준
    PaymentProvider.LEMON_SQUEEZY: 5.0,  # MoR·VAT 위임 가산
}

# Stripe·LemonSqueezy 고정 수수료 (USD 환산 ₩1,400 가정)
PG_FEE_FIXED_KRW: dict[PaymentProvider, int] = {
    PaymentProvider.PORTONE: 0,
    PaymentProvider.STRIPE: 420,  # $0.30 × 1,400
    PaymentProvider.LEMON_SQUEEZY: 700,  # $0.50 × 1,400
}


@dataclass(frozen=True)
class FeeBreakdown:
    """수수료 분해 (실 입금·세무 보고용)."""

    gross_krw: int  # 사용자 결제 총액
    pg_fee_krw: int  # PG 수수료 (3.3% 등)
    pg_fee_fixed_krw: int  # 고정 수수료 (Stripe·LS)
    vat_krw: int  # 부가세 (10%·일반과세자·매출의 1/11)
    net_krw: int  # 실 입금 (gross - pg_fee - fixed)
    label_kr: str


def calculate_fees(
    gross_krw: int,
    provider: PaymentProvider = PaymentProvider.PORTONE,
    is_general_tax: bool = True,  # 일반과세자 (간이과세자 X)
) -> FeeBreakdown:
    """결제 1건 수수료 분해 (PG 수수료 + 부가세 추정).

    Args:
        gross_krw: 사용자 결제 총액 (₩9,900 등·VAT 포함 표시 가격)
        provider: PG 종류
        is_general_tax: 일반과세자 (사업자 등록 SW업 의무)

    Returns:
        FeeBreakdown: pg_fee·fixed·vat·net 분해

    Note:
        VAT = 매출의 1/11 (10% 부가세·1.1로 나눈 값) = 외부 901 진단 정합
    """
    if gross_krw < 0:
        msg = "gross_krw ≥ 0 의무"
        raise ValueError(msg)
    fee_percent = PG_FEE_PERCENT[provider]
    fee_fixed = PG_FEE_FIXED_KRW[provider]
    pg_fee = int(gross_krw * fee_percent / 100)
    vat = gross_krw // 11 if is_general_tax else 0
    net = gross_krw - pg_fee - fee_fixed
    label = (
        f"₩{gross_krw:,} → 실 입금 ₩{net:,} "
        f"(PG {fee_percent}% ₩{pg_fee:,}"
        f"{f' + ₩{fee_fixed:,}' if fee_fixed else ''}"
        f"·VAT 별도 ₩{vat:,})"
    )
    return FeeBreakdown(
        gross_krw=gross_krw,
        pg_fee_krw=pg_fee,
        pg_fee_fixed_krw=fee_fixed,
        vat_krw=vat,
        net_krw=net,
        label_kr=label,
    )


def calculate_mrr_net(
    paying_users: int,
    monthly_price_krw: int,
    provider: PaymentProvider = PaymentProvider.PORTONE,
) -> int:
    """월 매출 실 입금 추정 (수수료 차감·VAT 별도)."""
    if paying_users < 0 or monthly_price_krw < 0:
        msg = "paying_users·monthly_price_krw ≥ 0 의무"
        raise ValueError(msg)
    gross = paying_users * monthly_price_krw
    breakdown = calculate_fees(gross, provider=provider)
    return breakdown.net_krw


# 환불 정책 (전자상거래법 §17·외부 901 진단 정합)
REFUND_WINDOW_DAYS = 7  # 결제 후 7일 무조건 환불 가능 (디지털 컨텐츠 = 사용 X 한정)
REFUND_USAGE_THRESHOLD = 0.30  # 30% 초과 사용 = 부분 환불·반환 X (대법원 판례 정합)


@dataclass(frozen=True)
class RefundDecision:
    """환불 자동 판단 결과 (전자상거래법 §17)."""

    eligible: bool
    full_refund: bool  # True = 전액·False = 부분 또는 거부
    refund_amount_krw: int
    reason_kr: str


# 한국 세무 (외부 901 진단·국세청 정합)
KOREAN_VAT_RATE = 0.10  # 10% 부가세 (일반과세자 기본)


@dataclass(frozen=True)
class VatBreakdown:
    """VAT 분리 결과 (가격 표시·세금계산서 발급용)."""

    gross_with_vat_krw: int  # VAT 포함 표시 가격
    supply_value_krw: int  # 공급가액 (매출)
    vat_krw: int  # 부가세 (납부 의무)
    label_kr: str


def format_invoice_line_kr(
    description: str,
    gross_with_vat_krw: int,
    is_general_tax: bool = True,
) -> str:
    """영수증 한 줄 표기 (공급가·VAT 분리·세금계산서 base).

    예: "Pro 월 정액 = ₩9,000 + VAT ₩900 = ₩9,900"
    """
    if not description:
        msg = "description 비어있을 수 없음"
        raise ValueError(msg)
    breakdown = split_korean_vat(gross_with_vat_krw, is_general_tax=is_general_tax)
    if breakdown.vat_krw == 0:
        return f"{description} = ₩{breakdown.gross_with_vat_krw:,} (VAT X)"
    return (
        f"{description} = ₩{breakdown.supply_value_krw:,}"
        f" + VAT ₩{breakdown.vat_krw:,}"
        f" = ₩{breakdown.gross_with_vat_krw:,}"
    )


def format_business_number_kr(number: str) -> str:
    """사업자등록번호 표준 포맷 (XXX-XX-XXXXX·국세청 표시 의무).

    입력: 1234567891 또는 123-45-67891 또는 12345-67891 등
    출력: 123-45-67891 (정확히 10자리 숫자만 인정)
    잘못된 입력 = 원본 반환 (변환 X·검증 X·호출자 = validate_korean_business_number 페어).
    """
    if not number:
        return ""
    cleaned = "".join(c for c in number if c.isdigit())
    if len(cleaned) != 10:
        return number  # 변환 X (검증 = validate_korean_business_number 책임)
    return f"{cleaned[:3]}-{cleaned[3:5]}-{cleaned[5:]}"


def split_korean_vat(
    gross_with_vat_krw: int,
    is_general_tax: bool = True,
) -> VatBreakdown:
    """한국 부가세 분리 (VAT 포함 가격 → 공급가 + VAT).

    공식 (일반과세자·국세청 표준):
        공급가 = gross / 1.1 (소수점 절사)
        VAT    = gross - 공급가

    간이과세자 = SW업 배제 (외부 901 진단)·but 옵션 보존.
    """
    if gross_with_vat_krw < 0:
        msg = "gross_with_vat_krw ≥ 0 의무"
        raise ValueError(msg)
    if not is_general_tax:
        return VatBreakdown(
            gross_with_vat_krw=gross_with_vat_krw,
            supply_value_krw=gross_with_vat_krw,
            vat_krw=0,
            label_kr=f"₩{gross_with_vat_krw:,} (간이과세자·VAT X)",
        )
    supply = int(gross_with_vat_krw / 1.10)
    vat = gross_with_vat_krw - supply
    return VatBreakdown(
        gross_with_vat_krw=gross_with_vat_krw,
        supply_value_krw=supply,
        vat_krw=vat,
        label_kr=(
            f"₩{gross_with_vat_krw:,} = 공급가 ₩{supply:,} + VAT ₩{vat:,}"
        ),
    )


def is_tax_invoice_required(
    customer_business_number: str = "",
    amount_krw: int = 0,
) -> bool:
    """세금계산서 발급 의무 여부 (한국 부가가치세법 §32).

    의무 조건 (둘 다 충족):
    1. 고객 = 사업자 (사업자등록번호 보유)
    2. 거래액 ≥ ₩100,000 (전자세금계산서 의무 임계값)

    근거: 부가세법 §32·국세청 (1만원~10만원·발급 권장 / 10만원+ 의무).
    """
    if amount_krw < 0:
        msg = "amount_krw ≥ 0 의무"
        raise ValueError(msg)
    if not customer_business_number:
        return False
    # 사업자등록번호 형식 검증 (XXX-XX-XXXXX·간이)
    cleaned = customer_business_number.replace("-", "").strip()
    if len(cleaned) != 10 or not cleaned.isdigit():
        return False
    return amount_krw >= 100_000


def format_price_with_period_kr(
    monthly_price_krw: int,
    period: str = "monthly",
) -> str:
    """가격·기간 한국어 포맷 (Streamlit caption·이메일·landing 통합).

    Args:
        monthly_price_krw: 월 정액 (Founding 할인은 호출자 책임)
        period: monthly·yearly·one-time

    예:
        format_price_with_period_kr(9_900) → "₩9,900/월"
        format_price_with_period_kr(9_900, "yearly") → "₩9,900/월·연 ₩118,800"
        format_price_with_period_kr(0) → "무료"
    """
    if monthly_price_krw < 0:
        msg = "monthly_price_krw ≥ 0 의무"
        raise ValueError(msg)
    if monthly_price_krw == 0:
        return "무료"
    if period not in {"monthly", "yearly", "one-time"}:
        msg = "period = monthly·yearly·one-time 의무"
        raise ValueError(msg)
    if period == "one-time":
        return f"₩{monthly_price_krw:,} 1회"
    if period == "yearly":
        annual = monthly_price_krw * 12
        return f"₩{monthly_price_krw:,}/월·연 ₩{annual:,}"
    return f"₩{monthly_price_krw:,}/월"


def generate_idempotency_key(prefix: str = "idem") -> str:
    """결제 idempotency 키 생성 (PG 중복 결제 방지·Stripe·PortOne 표준).

    형식: {prefix}_{32자 hex} (token_hex(16) = 128 bit·충돌 ≈ 1/2^64)
    호출자 = 결제 직전 1회 생성·재시도 시 동일 키 재사용 의무.
    """
    if not prefix or len(prefix) > 16:
        msg = "prefix = 1~16자 의무"
        raise ValueError(msg)
    return f"{prefix}_{secrets.token_hex(16)}"


@dataclass(frozen=True)
class PaymentAmountCheck:
    """결제 금액 검증 결과 (order tampering 방어)."""

    valid: bool
    reason_kr: str
    expected_krw: int
    actual_krw: int


def verify_payment_amount(
    expected_krw: int,
    actual_krw: int,
    tolerance_krw: int = 0,
) -> PaymentAmountCheck:
    """주문 금액 vs PG 결제 금액 일치 검증 (order tampering 방어).

    공격 시나리오:
    - 클라이언트 = ₩9,900 결제 시도·but PG payload = ₩100 변조
    - 본 helper = 서버측 expected와 PG 응답 actual 비교

    Args:
        expected_krw: DB에 저장된 주문 금액 (서버 신뢰)
        actual_krw: PG webhook 또는 confirm API에서 받은 금액
        tolerance_krw: 허용 오차 (기본 0·환율 변동·반올림 등 예외 시만 사용)

    Returns:
        PaymentAmountCheck: valid=False 시 즉시 결제 거부·환불 권장
    """
    if expected_krw < 0 or actual_krw < 0 or tolerance_krw < 0:
        msg = "expected·actual·tolerance ≥ 0 의무"
        raise ValueError(msg)
    diff = abs(expected_krw - actual_krw)
    if diff <= tolerance_krw:
        return PaymentAmountCheck(
            valid=True,
            reason_kr=f"금액 일치 (₩{actual_krw:,}·오차 ₩{diff:,})",
            expected_krw=expected_krw,
            actual_krw=actual_krw,
        )
    return PaymentAmountCheck(
        valid=False,
        reason_kr=(
            f"금액 불일치·order tampering 의심"
            f" (expected ₩{expected_krw:,}·actual ₩{actual_krw:,}·diff ₩{diff:,})"
        ),
        expected_krw=expected_krw,
        actual_krw=actual_krw,
    )


def verify_webhook_signature(
    payload: bytes,
    signature_header: str,
    webhook_secret: str,
    algorithm: str = "sha256",
) -> bool:
    """webhook HMAC 서명 검증 (PortOne·Stripe 표준·timing-safe).

    Args:
        payload: 원본 본문 bytes (json.dumps 후 .encode·역직렬화 X)
        signature_header: 헤더 값 (예: PortOne `x-portone-signature`·Stripe `Stripe-Signature`)
        webhook_secret: PG 발급 webhook 비밀 키 (.env에서만)
        algorithm: hashlib 알고리즘 (sha256 표준·sha512 가능)

    Returns:
        bool: 일치 = True·timing-safe 비교 (hmac.compare_digest)

    Note:
        실 운영 = PG별 헤더 형식 변환 후 호출 (PortOne = 직접 hex·Stripe = "t=,v1=" 파싱)
    """
    if not webhook_secret or not signature_header or not payload:
        return False
    try:
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            payload,
            getattr(hashlib, algorithm),
        ).hexdigest()
    except (AttributeError, TypeError):
        return False
    # signature_header 정규화 (대소문자·prefix 제거)
    cleaned = signature_header.strip().lower()
    if cleaned.startswith("sha256="):
        cleaned = cleaned[7:]
    return hmac.compare_digest(expected, cleaned)


def generate_receipt_id(
    now: datetime | None = None,
    prefix: str = "RCPT",
) -> str:
    """영수증 ID 자동 생성 (조회 가능 형식·전자상거래법 §13).

    형식: {prefix}-YYYYMMDD-{8자 hex}
    예: RCPT-20260509-A4B7C1D9

    충돌 = 약 1/4억 (8자 hex)·실 운영 = DB unique 제약 추가 권장.
    """
    if not prefix or len(prefix) > 8:
        msg = "prefix = 1~8자 의무"
        raise ValueError(msg)
    current = now or datetime.now(UTC)
    date_part = current.strftime("%Y%m%d")
    hex_part = secrets.token_hex(4).upper()
    return f"{prefix}-{date_part}-{hex_part}"


def is_refund_eligible(
    paid_at: datetime,
    now: datetime | None = None,
    window_days: int = REFUND_WINDOW_DAYS,
) -> bool:
    """7일 환불 창 내 여부 (전자상거래법 §17)."""
    if paid_at.tzinfo is None:
        msg = "paid_at = UTC tzinfo 의무 (헌법 §3)"
        raise ValueError(msg)
    if window_days <= 0:
        msg = "window_days > 0 의무"
        raise ValueError(msg)
    current = now or datetime.now(UTC)
    elapsed = current - paid_at
    return elapsed <= timedelta(days=window_days)


def calculate_refund_amount(
    gross_paid_krw: int,
    paid_at: datetime,
    usage_ratio: float = 0.0,
    now: datetime | None = None,
) -> RefundDecision:
    """환불 금액 자동 산정 (전자상거래법 §17·디지털 컨텐츠).

    Args:
        gross_paid_krw: 결제 총액
        paid_at: 결제 시점 (UTC)
        usage_ratio: 사용 비율 0.0~1.0 (예: 30일 중 9일 = 0.3)
        now: 현재 시점 (테스트용)

    Returns:
        RefundDecision: 자동 판단 결과·CS 메일 자동 발송 가능

    정합 (대법원 판례·전자상거래법 §17):
        1. 7일 내 + 미사용 (≤30%) = 전액 환불
        2. 7일 내 + 사용 중 (>30%) = 부분 환불 (사용 차감)
        3. 7일 초과 = 환불 거부 (단, 약관 별도)
    """
    if gross_paid_krw < 0:
        msg = "gross_paid_krw ≥ 0 의무"
        raise ValueError(msg)
    if not 0.0 <= usage_ratio <= 1.0:
        msg = "usage_ratio = 0.0~1.0 의무"
        raise ValueError(msg)

    if not is_refund_eligible(paid_at, now=now):
        return RefundDecision(
            eligible=False,
            full_refund=False,
            refund_amount_krw=0,
            reason_kr="환불 창 7일 초과 (전자상거래법 §17 적용 종료)",
        )

    if usage_ratio <= REFUND_USAGE_THRESHOLD:
        return RefundDecision(
            eligible=True,
            full_refund=True,
            refund_amount_krw=gross_paid_krw,
            reason_kr=f"7일 내 + 사용 {usage_ratio:.0%} ≤ {REFUND_USAGE_THRESHOLD:.0%}·전액 환불",
        )

    refund = int(gross_paid_krw * (1.0 - usage_ratio))
    return RefundDecision(
        eligible=True,
        full_refund=False,
        refund_amount_krw=refund,
        reason_kr=f"7일 내·사용 {usage_ratio:.0%} 차감·부분 환불 ₩{refund:,}",
    )


__all__ = [
    "KOREAN_VAT_RATE",
    "PG_FEE_FIXED_KRW",
    "PG_FEE_PERCENT",
    "PRICE_BENCHMARKS_KRW",
    "REFUND_USAGE_THRESHOLD",
    "REFUND_WINDOW_DAYS",
    "CheckoutItem",
    "FeeBreakdown",
    "PaymentAmountCheck",
    "PaymentConfig",
    "PaymentProvider",
    "RefundDecision",
    "VatBreakdown",
    "calculate_fees",
    "calculate_mrr_net",
    "calculate_refund_amount",
    "format_business_number_kr",
    "format_invoice_line_kr",
    "format_price_with_period_kr",
    "generate_idempotency_key",
    "generate_receipt_id",
    "is_refund_eligible",
    "is_tax_invoice_required",
    "select_provider",
    "split_korean_vat",
    "verify_payment_amount",
    "verify_webhook_signature",
]
