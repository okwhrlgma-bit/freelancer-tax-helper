"""freelancer-tax-helper — 한국 프리랜서 비용 처리·종소세 환급 추정.

ADR 0053·0055 정합·30 apps #31·페인 P-2026-004 (90/100 GO).
헌법 §14·자관 데이터 X·offline·MIT.
면책: 자기 측정 보조·세무사 자문 X·홈택스 신고는 별도.
"""

from __future__ import annotations

from freelancer_tax_helper.categories import CATEGORIES, CategoryName, classify_vendor
from freelancer_tax_helper.core import Receipt, TaxReport, analyze
from freelancer_tax_helper.refund import (
    SIMPLE_RATE,
    estimate_income_tax,
    estimate_refund,
    get_simple_rate,
)

__version__ = "0.1.0"
__all__ = [
    "CATEGORIES",
    "SIMPLE_RATE",
    "CategoryName",
    "Receipt",
    "TaxReport",
    "analyze",
    "classify_vendor",
    "estimate_income_tax",
    "estimate_refund",
    "get_simple_rate",
]
