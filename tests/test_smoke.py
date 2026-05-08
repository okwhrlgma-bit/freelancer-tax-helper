"""freelancer-tax-helper smoke test (실 사용 시나리오·배포 직전 완성도).

ADR 0061 정합·코드 우선·Cycle 97.
"""

from __future__ import annotations

from freelancer_tax_helper import Receipt, analyze
from freelancer_tax_helper.core import auto_categorize_receipts
from freelancer_tax_helper.refund import estimate_refund


class TestRealWorldScenarios:
    """실 사용자 시나리오 (Mom Test 정합)."""

    def test_it_developer_30m_income(self) -> None:
        """IT 개발자·연 3,000만·6 영수증 = 환급 발생."""
        receipts = [
            Receipt(date="2026-01-15", amount=35_000, vendor="스타벅스", category="meal"),
            Receipt(date="2026-02-03", amount=80_000, vendor="교보문고", category="books"),
            Receipt(date="2026-02-15", amount=88_000, vendor="skt", category="comm"),
            Receipt(date="2026-03-10", amount=250_000, vendor="위워크", category="rent"),
            Receipt(date="2026-03-15", amount=45_000, vendor="카카오T", category="transport"),
            Receipt(date="2026-04-20", amount=99_000, vendor="인프런 강의", category="education"),
        ]
        report = analyze(receipts, income=30_000_000, business_code="940100")
        assert report.refund_estimate > 0  # 환급 발생
        assert report.deductible_total == 597_000
        assert report.simple_rate_comparison["simple_rate_cost"] == 20_280_000
        # 단순경비율 우세 (직접 비용 ₩597K << 단순 ₩20.28M)
        assert report.simple_rate_comparison["deductible_used"] == 20_280_000

    def test_writer_15m_income_with_low_costs(self) -> None:
        """작가·연 1,500만·영수증 적음 = 단순경비율 우세."""
        receipts = [
            Receipt(date="2026-03-10", amount=50_000, vendor="교보문고", category="books"),
        ]
        report = analyze(receipts, income=15_000_000, business_code="940300")
        # 단순경비율 58.7% x 1,500만 = 880.5만·직접 ₩50K << 단순
        assert report.simple_rate_comparison["deductible_used"] > 8_000_000

    def test_high_income_100m_progressive_tax(self) -> None:
        """1억 수입·누진세율 적용·환급 추가 납부 가능성."""
        receipts = [
            Receipt(date="2026-03-15", amount=10_000_000, vendor="외주비", category="outsourcing"),
        ]
        report = analyze(receipts, income=100_000_000, business_code="940100")
        # 1억·누진세율 적용
        assert report.simple_rate_comparison["estimated_tax"] > 0
        assert report.deductible_total == 10_000_000

    def test_auto_categorization_workflow(self) -> None:
        """전체 워크플로우: vendor → 자동 분류 → 분석."""
        raw_receipts = [
            Receipt(date="2026-03-15", amount=12_000, vendor="스타벅스 강남점"),
            Receipt(date="2026-03-20", amount=88_000, vendor="skt"),
            Receipt(date="2026-04-01", amount=50_000, vendor="교보문고"),
        ]
        # 자동 분류
        classified = auto_categorize_receipts(raw_receipts)
        assert classified[0].category == "meal"
        assert classified[1].category == "comm"
        assert classified[2].category == "books"

        # 분석
        report = analyze(classified, income=30_000_000)
        assert report.deductible_total == 150_000

    def test_refund_estimate_precision(self) -> None:
        """환급 추정 정확성 (3.3% 원천공제 vs 누진세율)."""
        result = estimate_refund(
            income=20_000_000,
            deductible_cost=0,
            business_code="940100",
        )
        # 원천공제 = 20M x 3.3% = 660K
        assert result["withholding"] == 660_000
        # 단순경비율 67.6% = 13.52M·과세표준 = 20M - 13.52M - 150만 = 4.98M
        # 세액 = 4.98M x 6% = 298,800
        assert result["estimated_tax"] < result["withholding"]  # 환급 발생
