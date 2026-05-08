"""환급 추정 + 한국 종소세 누진세율 + 단순경비율.

출처: 국세청 「2026년 사업소득 단순경비율」·소득세법 §55 누진세율.
면책: 단순화·실제 신고는 홈택스 또는 세무사 위임.
"""

from __future__ import annotations

# 사업코드별 단순경비율 (수입 ≤ 7,500만원·2026 기준 추정)
SIMPLE_RATE: dict[str, float] = {
    "940100": 0.676,  # IT 개발자·소프트웨어
    "940200": 0.642,  # 디자인·일러스트
    "940300": 0.587,  # 작가·번역
    "940904": 0.587,  # 작가
    "940906": 0.641,  # 강사·번역
    "940909": 0.641,  # 기타 자영업
    "940500": 0.658,  # 컨설팅
    "940600": 0.612,  # 사진·영상
}

DEFAULT_SIMPLE_RATE = 0.641  # 미지정 시 기본 (940909)


def get_simple_rate(business_code: str) -> float:
    """사업코드 → 단순경비율."""
    return SIMPLE_RATE.get(business_code, DEFAULT_SIMPLE_RATE)


# 종합소득세 누진세율 (2026·소득세법 §55)
# (limit, rate, deduction)
_PROGRESSIVE_BRACKETS: tuple[tuple[int, float, int], ...] = (
    (14_000_000, 0.06, 0),
    (50_000_000, 0.15, 1_260_000),
    (88_000_000, 0.24, 5_760_000),
    (150_000_000, 0.35, 15_440_000),
    (300_000_000, 0.38, 19_940_000),
    (500_000_000, 0.40, 25_940_000),
    (1_000_000_000, 0.42, 35_940_000),
    (10_000_000_000, 0.45, 65_940_000),
)

# 기본 인적공제 (본인·1인 기준)
PERSONAL_DEDUCTION_KRW = 1_500_000

# 사업소득세 원천공제율 (3.3% = 소득세 3% + 지방세 0.3%)
WITHHOLDING_RATE = 0.033


def estimate_income_tax(taxable_income: int) -> int:
    """누진세율 적용 종합소득세 (지방소득세 10% 별도).

    Args:
        taxable_income: 과세표준 (수입 - 비용 - 인적공제)

    Returns:
        소득세 (지방소득세 제외·원 단위 정수)
    """
    if taxable_income <= 0:
        return 0

    for limit, rate, deduction in _PROGRESSIVE_BRACKETS:
        if taxable_income <= limit:
            return max(0, int(taxable_income * rate - deduction))

    # 10억 초과 (drop-through·이론적 case)
    return int(taxable_income * 0.45 - 65_940_000)


def estimate_refund(
    income: int,
    deductible_cost: int,
    business_code: str = "940909",
    personal_deduction: int = PERSONAL_DEDUCTION_KRW,
) -> dict[str, int]:
    """환급 추정 (3.3% 원천공제 vs 실제 세액).

    Args:
        income: 연 수입 (원천공제 전 총액)
        deductible_cost: 인정 가능 비용 (직접 영수증 합계)
        business_code: 사업코드 (단순경비율 매핑)
        personal_deduction: 인적공제 (기본 본인 150만)

    Returns:
        {
          "withholding": 원천공제 합계,
          "direct_cost": 직접 비용,
          "simple_rate_cost": 단순경비율 비용,
          "deductible_used": 둘 중 큰 값 (환급 ↑),
          "taxable_income": 과세표준,
          "estimated_tax": 누진세율 적용 세액,
          "local_tax": 지방소득세 (10%),
          "total_tax": 합계,
          "refund": 환급 (양수) or 추가 납부 (음수)
        }
    """
    withholding = int(income * WITHHOLDING_RATE)
    simple_cost = int(income * get_simple_rate(business_code))
    deductible_used = max(deductible_cost, simple_cost)

    taxable = max(0, income - deductible_used - personal_deduction)
    income_tax = estimate_income_tax(taxable)
    local_tax = int(income_tax * 0.10)
    total_tax = income_tax + local_tax
    refund = withholding - total_tax

    return {
        "withholding": withholding,
        "direct_cost": deductible_cost,
        "simple_rate_cost": simple_cost,
        "deductible_used": deductible_used,
        "taxable_income": taxable,
        "estimated_tax": income_tax,
        "local_tax": local_tax,
        "total_tax": total_tax,
        "refund": refund,
    }
