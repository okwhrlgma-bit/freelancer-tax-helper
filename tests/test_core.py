"""freelancer-tax-helper 테스트 (≥15)."""

from __future__ import annotations

import pytest

from freelancer_tax_helper.categories import (
    CATEGORIES,
    CategoryName,
    classify_vendor,
    is_valid_category,
)
from freelancer_tax_helper.core import Receipt, analyze, auto_categorize_receipts
from freelancer_tax_helper.refund import (
    DEFAULT_SIMPLE_RATE,
    SIMPLE_RATE,
    estimate_income_tax,
    estimate_refund,
    get_simple_rate,
)


class TestReceipt:
    def test_minimal_construction(self) -> None:
        r = Receipt(date="2026-03-15", amount=10000, vendor="스타벅스")
        assert r.amount == 10000
        assert r.category == "other"

    def test_date_required(self) -> None:
        with pytest.raises(ValueError, match="date는 필수"):
            Receipt(date="", amount=10000, vendor="x")

    def test_amount_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="amount는 양수"):
            Receipt(date="2026-03-15", amount=0, vendor="x")
        with pytest.raises(ValueError, match="amount는 양수"):
            Receipt(date="2026-03-15", amount=-100, vendor="x")

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValueError, match="category는 10 분류"):
            Receipt(date="2026-03-15", amount=10000, vendor="x", category="invalid")

    def test_immutable(self) -> None:
        from dataclasses import FrozenInstanceError

        r = Receipt(date="2026-03-15", amount=10000, vendor="x")
        with pytest.raises(FrozenInstanceError):
            r.amount = 99999  # type: ignore[misc]


class TestCategories:
    def test_10_categories(self) -> None:
        assert len(CATEGORIES) == 10
        assert "meal" in CATEGORIES
        assert "rent" in CATEGORIES

    def test_classify_meal(self) -> None:
        assert classify_vendor("스타벅스 강남점") == CategoryName.MEAL.value
        assert classify_vendor("Starbucks Gangnam") == CategoryName.MEAL.value

    def test_classify_transport(self) -> None:
        assert classify_vendor("카카오T 택시") == CategoryName.TRANSPORT.value
        assert classify_vendor("KTX 서울역") == CategoryName.TRANSPORT.value

    def test_classify_books(self) -> None:
        assert classify_vendor("교보문고") == CategoryName.BOOKS.value
        assert classify_vendor("yes24 도서") == CategoryName.BOOKS.value

    def test_classify_unknown_returns_other(self) -> None:
        assert classify_vendor("zzqq xyz unknown") == CategoryName.OTHER.value

    def test_is_valid_category(self) -> None:
        assert is_valid_category("meal")
        assert not is_valid_category("invalid")


class TestRefund:
    def test_simple_rate_known_code(self) -> None:
        assert get_simple_rate("940100") == 0.676  # IT
        assert get_simple_rate("940904") == 0.587  # 작가

    def test_simple_rate_unknown_default(self) -> None:
        assert get_simple_rate("99999") == DEFAULT_SIMPLE_RATE

    def test_progressive_tax_low_bracket(self) -> None:
        # 1,000만원 = 6% bracket = 60만원
        assert estimate_income_tax(10_000_000) == 600_000

    def test_progressive_tax_mid_bracket(self) -> None:
        # 3,000만원 = 15% - 126만 = 450 - 126 = 324만
        assert estimate_income_tax(30_000_000) == 3_240_000

    def test_progressive_tax_zero_or_negative(self) -> None:
        assert estimate_income_tax(0) == 0
        assert estimate_income_tax(-1_000_000) == 0

    def test_estimate_refund_low_income(self) -> None:
        # 3,000만 수입·IT 940100 = 단순경비율 67.6% = 2,028만 비용
        # 과세표준 = 3,000 - 2,028 - 150 = 822만
        # 세액 = 822 x 6% = 49.32만 + 지방세
        result = estimate_refund(income=30_000_000, deductible_cost=0, business_code="940100")
        assert result["withholding"] == int(30_000_000 * 0.033)  # 99만
        assert result["simple_rate_cost"] == int(30_000_000 * 0.676)
        assert result["deductible_used"] == result["simple_rate_cost"]  # 직접 0 < 단순
        assert result["refund"] > 0  # 환급 발생 (3.3% > 누진세율 적용)

    def test_estimate_refund_uses_higher_cost(self) -> None:
        # 직접 비용 > 단순경비율 = 직접 적용
        result = estimate_refund(
            income=30_000_000, deductible_cost=25_000_000, business_code="940100"
        )
        # 단순 = 30M x 0.676 = 20.28M·직접 = 25M = 직접 우세
        assert result["deductible_used"] == 25_000_000

    def test_estimate_refund_high_income(self) -> None:
        # 1억 수입·IT = 단순 6,760만·과세표준 = 1억 - 6,760 - 150 = 3,090만
        result = estimate_refund(income=100_000_000, deductible_cost=0, business_code="940100")
        assert result["estimated_tax"] > 0
        assert result["total_tax"] > 0


class TestAnalyze:
    def test_empty_receipts_with_income(self) -> None:
        report = analyze([], income=20_000_000, business_code="940100")
        assert report.deductible_total == 0
        assert report.receipt_count == 0
        assert any("0건" in w for w in report.missing_warnings)

    def test_negative_income_rejected(self) -> None:
        with pytest.raises(ValueError, match="income은 음수"):
            analyze([], income=-1)

    def test_basic_breakdown(self) -> None:
        receipts = [
            Receipt(date="2026-03-15", amount=10_000, vendor="스타벅스", category="meal"),
            Receipt(date="2026-03-20", amount=50_000, vendor="교보문고", category="books"),
        ]
        report = analyze(receipts, income=30_000_000, business_code="940100")
        assert report.deductible_total == 60_000
        assert report.category_breakdown["meal"] == 10_000
        assert report.category_breakdown["books"] == 50_000

    def test_entertainment_50_percent(self) -> None:
        receipts = [
            Receipt(date="2026-03-15", amount=100_000, vendor="회식", category="entertainment"),
        ]
        report = analyze(receipts, income=30_000_000)
        # 접대비 50% = 50,000
        assert report.deductible_total == 50_000
        assert report.category_breakdown["entertainment"] == 50_000

    def test_warnings_generated(self) -> None:
        receipts = [
            Receipt(date="2026-03-15", amount=10_000, vendor="스타벅스", category="meal"),
        ]
        report = analyze(receipts, income=30_000_000)
        # comm·transport 누락 경고
        assert any("통신" in w for w in report.missing_warnings)
        assert any("교통" in w for w in report.missing_warnings)

    def test_recommendations_always_returned(self) -> None:
        receipts = [Receipt(date="2026-03-15", amount=10_000, vendor="x", category="meal")]
        report = analyze(receipts, income=30_000_000)
        assert len(report.recommendations) >= 2
        # 면책 항상 포함
        assert any("자기 측정" in r and "세무사" in r for r in report.recommendations)

    def test_simple_rate_comparison_present(self) -> None:
        report = analyze([], income=50_000_000, business_code="940100")
        cmp = report.simple_rate_comparison
        assert cmp["direct_cost"] == 0
        assert cmp["simple_rate_cost"] == int(50_000_000 * 0.676)
        assert cmp["deductible_used"] == cmp["simple_rate_cost"]

    def test_full_breakdown_includes_all_categories(self) -> None:
        # 모든 10 카테고리 = breakdown dict에 노출 (UI 안정)
        receipts = [Receipt(date="2026-03-15", amount=10_000, vendor="x", category="meal")]
        report = analyze(receipts, income=20_000_000)
        assert len(report.category_breakdown) == 10
        for cat in CATEGORIES:
            assert cat in report.category_breakdown


class TestAutoCategorize:
    def test_other_to_known_category(self) -> None:
        receipts = [
            Receipt(date="2026-03-15", amount=10_000, vendor="스타벅스", category="other"),
        ]
        result = auto_categorize_receipts(receipts)
        assert result[0].category == CategoryName.MEAL.value

    def test_preserve_existing_category(self) -> None:
        # 이미 분류된 영수증 = 변경 X
        receipts = [
            Receipt(date="2026-03-15", amount=10_000, vendor="스타벅스", category="rent"),
        ]
        result = auto_categorize_receipts(receipts)
        assert result[0].category == "rent"

    def test_preserve_other_when_unmatched(self) -> None:
        receipts = [
            Receipt(date="2026-03-15", amount=10_000, vendor="zzqq xyz", category="other"),
        ]
        result = auto_categorize_receipts(receipts)
        assert result[0].category == CategoryName.OTHER.value


class TestPrivacyAndConstitution:
    def test_deterministic_output(self) -> None:
        # 헌법 §9 정합·동일 입력 = 동일 출력
        receipts = [
            Receipt(date="2026-03-15", amount=10_000, vendor="스타벅스", category="meal"),
        ]
        r1 = analyze(receipts, income=30_000_000)
        r2 = analyze(receipts, income=30_000_000)
        assert r1.refund_estimate == r2.refund_estimate
        assert r1.deductible_total == r2.deductible_total

    def test_input_immutable(self) -> None:
        receipts = [Receipt(date="2026-03-15", amount=10_000, vendor="x", category="meal")]
        original_amount = receipts[0].amount
        analyze(receipts, income=30_000_000)
        assert receipts[0].amount == original_amount

    def test_simple_rate_table_complete(self) -> None:
        # 8 사업코드 등록 확인
        assert len(SIMPLE_RATE) >= 7
        for _code, rate in SIMPLE_RATE.items():
            assert 0.5 <= rate <= 0.7  # 단순경비율 범위
