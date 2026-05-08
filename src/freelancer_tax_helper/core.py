"""freelancer-tax-helper 핵심 로직.

평가축 (ADR 0053):
- 단일 기능 = "Receipt list + 수입 → TaxReport (환급 추정·누락 경고)"
- 자관 데이터 X (헌법 §14·사용자 영수증·SaaS 서버 X)
- offline (외부 API X)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from freelancer_tax_helper.categories import (
    CATEGORIES,
    CategoryName,
    classify_vendor,
    is_valid_category,
)
from freelancer_tax_helper.refund import estimate_refund

# 접대비 인정 한도 (50%)
ENTERTAINMENT_DEDUCTION_RATIO = 0.5


@dataclass(frozen=True)
class Receipt:
    """영수증 1건 (단일 기능 input element)."""

    date: str  # ISO 8601 YYYY-MM-DD
    amount: int  # 원 (양수)
    vendor: str
    category: str = "other"
    attachment_path: str = ""
    memo: str = ""

    def __post_init__(self) -> None:
        if not self.date:
            raise ValueError("date는 필수입니다 (YYYY-MM-DD)")
        if self.amount <= 0:
            raise ValueError(f"amount는 양수여야 합니다 (받음: {self.amount})")
        if not is_valid_category(self.category):
            raise ValueError(f"category는 10 분류 중 하나여야 합니다 (받음: {self.category!r})")


@dataclass(frozen=True)
class TaxReport:
    """종소세 분석 결과 (단일 기능 output)."""

    deductible_total: int
    category_breakdown: dict[str, int]
    missing_warnings: list[str]
    refund_estimate: int
    simple_rate_comparison: dict[str, int]
    recommendations: list[str]
    income: int
    withholding_total: int
    receipt_count: int
    business_code: str


def _calculate_deductible_amount(receipt: Receipt) -> int:
    """영수증 1건의 인정 비용 (접대비 = 50%·나머지 = 100%)."""
    if receipt.category == CategoryName.ENTERTAINMENT.value:
        return int(receipt.amount * ENTERTAINMENT_DEDUCTION_RATIO)
    return receipt.amount


def _detect_missing_warnings(
    breakdown: dict[str, int],
    receipt_count: int,
    has_monthly_data: bool,
) -> list[str]:
    """누락 영수증 경고 생성."""
    warnings: list[str] = []

    if receipt_count == 0:
        warnings.append("⚠️ 영수증 0건·비용 처리 X·단순경비율만 적용됩니다.")
        return warnings

    if breakdown.get(CategoryName.COMM.value, 0) == 0:
        warnings.append("📞 통신비 영수증 누락·휴대폰·인터넷·서버 비용 점검 권고.")
    if breakdown.get(CategoryName.TRANSPORT.value, 0) == 0:
        warnings.append("🚗 교통비 영수증 누락·업무 이동 영수증 점검.")
    if not has_monthly_data:
        warnings.append("📅 월별 데이터 부족·매월 영수증 정리 권고.")

    return warnings


def _generate_recommendations(
    refund: int,
    direct_cost: int,
    simple_cost: int,
    receipt_count: int,
) -> list[str]:
    """사용자 친화 권고 (한국어·헌법 §11 정합)."""
    recommendations: list[str] = []

    if refund > 0:
        recommendations.append(f"💰 예상 환급 ₩{refund:,}·5월 종소세 신고 시 받을 가능성.")
    elif refund < 0:
        recommendations.append(f"⚠️ 예상 추가 납부 ₩{-refund:,}·신고 전 비용 추가 검토 권고.")
    else:
        recommendations.append("⚖️ 환급·추가 납부 = 0·정확한 신고 가능.")

    if simple_cost > direct_cost:
        diff = simple_cost - direct_cost
        recommendations.append(
            f"📊 단순경비율 ({simple_cost:,}원) > 직접 비용 ({direct_cost:,}원)·"
            f"₩{diff:,} 더 인정·**단순경비율 적용 유리**."
        )
    elif direct_cost > simple_cost:
        diff = direct_cost - simple_cost
        recommendations.append(
            f"📊 직접 비용 ({direct_cost:,}원) > 단순경비율 ({simple_cost:,}원)·"
            f"₩{diff:,} 더 인정·**직접 비용 신고 유리**."
        )

    if receipt_count < 30:
        recommendations.append("📝 영수증 30건 미만·매월 정리 시 환급 ↑ 가능성.")

    recommendations.append("※ 본 도구 = 자기 측정 보조·세무사 자문 X·홈택스 신고 별도.")

    return recommendations


def analyze(
    receipts: list[Receipt],
    income: int,
    business_code: str = "940909",
) -> TaxReport:
    """영수증 list + 수입 → TaxReport.

    Args:
        receipts: 영수증 list (0건 허용)
        income: 연 수입 (원천공제 전 총액)
        business_code: 사업코드 (단순경비율 매핑·기본 940909 기타)

    Returns:
        TaxReport
    """
    if income < 0:
        raise ValueError(f"income은 음수 불가 (받음: {income})")

    # category별 합계 (인정 비용 기준·접대비 50%)
    breakdown: dict[str, int] = defaultdict(int)
    deductible_total = 0
    months = set()

    for r in receipts:
        deductible_amount = _calculate_deductible_amount(r)
        breakdown[r.category] += deductible_amount
        deductible_total += deductible_amount
        # 월 추출 (YYYY-MM)
        if len(r.date) >= 7:
            months.add(r.date[:7])

    # 모든 카테고리 = 0건이라도 dict에 노출 (UI 안정)
    full_breakdown = {cat: breakdown.get(cat, 0) for cat in CATEGORIES}

    # 환급 추정
    refund_data = estimate_refund(income, deductible_total, business_code)

    # 누락 경고
    has_monthly = len(months) >= 6  # 반년 이상
    warnings = _detect_missing_warnings(full_breakdown, len(receipts), has_monthly)

    # 권고
    recommendations = _generate_recommendations(
        refund_data["refund"],
        deductible_total,
        refund_data["simple_rate_cost"],
        len(receipts),
    )

    return TaxReport(
        deductible_total=deductible_total,
        category_breakdown=full_breakdown,
        missing_warnings=warnings,
        refund_estimate=refund_data["refund"],
        simple_rate_comparison={
            "direct_cost": refund_data["direct_cost"],
            "simple_rate_cost": refund_data["simple_rate_cost"],
            "deductible_used": refund_data["deductible_used"],
            "estimated_tax": refund_data["estimated_tax"],
            "local_tax": refund_data["local_tax"],
            "total_tax": refund_data["total_tax"],
        },
        recommendations=recommendations,
        income=income,
        withholding_total=refund_data["withholding"],
        receipt_count=len(receipts),
        business_code=business_code,
    )


def auto_categorize_receipts(receipts: list[Receipt]) -> list[Receipt]:
    """category="other"인 영수증을 vendor 키워드로 자동 분류.

    원본 보존·신규 list 반환 (frozen=True 정합).
    """
    result: list[Receipt] = []
    for r in receipts:
        if r.category == CategoryName.OTHER.value:
            auto_cat = classify_vendor(r.vendor)
            if auto_cat != CategoryName.OTHER.value:
                result.append(
                    Receipt(
                        date=r.date,
                        amount=r.amount,
                        vendor=r.vendor,
                        category=auto_cat,
                        attachment_path=r.attachment_path,
                        memo=r.memo,
                    )
                )
                continue
        result.append(r)
    return result


# 사용되지 않는 import 제거를 위해 명시적 export
__all_internal__ = (field,)
