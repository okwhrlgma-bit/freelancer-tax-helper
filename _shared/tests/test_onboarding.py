"""온보딩 모듈 smoke tests (Cycle 124)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onboarding import (
    DEFAULT_MILESTONES,
    ConversionFunnel,
    calculate_arpu_krw,
    calculate_churn_rate,
    calculate_founding_slot,
    calculate_ltv_cac_ratio,
    calculate_ltv_krw,
    calculate_mrr_growth_pct,
    calculate_nrr_pct,
    calculate_payback_months,
    calculate_progress_percent,
    calculate_rule_of_40,
    calculate_trial_status,
    diagnose_funnel,
    diagnose_nrr,
    format_bessemer_summary_kr,
    format_growth_summary_kr,
    format_pricing_summary_kr,
    generate_referral_code,
    get_current_milestone,
)


class TestTrialStatus:
    def test_fresh_signup_14_days(self):
        started = datetime.now(UTC) - timedelta(days=0)
        status = calculate_trial_status(started)
        assert status.days_remaining == 14
        assert not status.is_expired
        assert not status.is_warning

    def test_warning_3_days_left(self):
        started = datetime.now(UTC) - timedelta(days=11)
        status = calculate_trial_status(started)
        assert status.days_remaining == 3
        assert status.is_warning
        assert "곧 종료" in status.label_kr

    def test_expired(self):
        started = datetime.now(UTC) - timedelta(days=14)
        status = calculate_trial_status(started)
        assert status.days_remaining == 0
        assert status.is_expired
        assert "체험 종료" in status.label_kr

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError, match="UTC tzinfo"):
            calculate_trial_status(datetime(2026, 5, 9))


class TestFoundingSlot:
    def test_fresh_launch_100_slots(self):
        slot = calculate_founding_slot(taken=0)
        assert slot.remaining == 100
        assert not slot.is_sold_out
        assert slot.discount_percent == 50

    def test_partial_taken(self):
        slot = calculate_founding_slot(taken=37)
        assert slot.remaining == 63
        assert "63/100" in slot.label_kr
        assert "50% 할인" in slot.label_kr

    def test_sold_out(self):
        slot = calculate_founding_slot(taken=100)
        assert slot.is_sold_out
        assert slot.remaining == 0
        assert "마감" in slot.label_kr

    def test_overflow_capped(self):
        slot = calculate_founding_slot(taken=150)
        assert slot.taken == 100
        assert slot.is_sold_out

    def test_negative_taken_rejected(self):
        with pytest.raises(ValueError, match="taken"):
            calculate_founding_slot(taken=-1)


class TestMilestones:
    def test_default_3_milestones(self):
        assert len(DEFAULT_MILESTONES) == 3
        m1, m6, m12 = DEFAULT_MILESTONES
        assert m1.month == 1
        assert m1.target_paying == 3
        assert m12.target_mrr_krw == 990_000

    def test_get_current_month_0(self):
        m = get_current_milestone(0)
        assert m.month == 1

    def test_get_current_month_3(self):
        m = get_current_milestone(3)
        assert m.month == 6

    def test_get_current_month_12_clamps_last(self):
        m = get_current_milestone(15)
        assert m.month == 12

    def test_progress_50_percent(self):
        m = get_current_milestone(0)
        progress = calculate_progress_percent(actual_paying=1, milestone=m)
        assert progress == 33  # 1/3

    def test_progress_capped_100(self):
        m = get_current_milestone(0)
        progress = calculate_progress_percent(actual_paying=10, milestone=m)
        assert progress == 100


class TestPricingSummary:
    def test_founding_active_50_percent(self):
        slot = calculate_founding_slot(taken=37)
        summary = format_pricing_summary_kr(9_900, slot)
        assert "Founding ₩4,950/월" in summary
        assert "63/100 잔여" in summary
        assert "14일 무료 체험" in summary

    def test_founding_sold_out_falls_back(self):
        slot = calculate_founding_slot(taken=100)
        summary = format_pricing_summary_kr(9_900, slot)
        assert "₩9,900/월" in summary
        assert "Founding 마감" in summary

    def test_negative_price_rejected(self):
        slot = calculate_founding_slot(taken=0)
        with pytest.raises(ValueError, match="monthly_price_krw"):
            format_pricing_summary_kr(-100, slot)


class TestConversionFunnel:
    """Cycle 140: 5 단계 funnel KPI (외부 발사 운영 정합)."""

    def test_zero_visits_zero_rates(self):
        funnel = ConversionFunnel(visits=0, signups=0, trials=0, paid=0, renewed=0)
        assert funnel.signup_rate == 0.0
        assert funnel.overall_paid_rate == 0.0

    def test_habit_pixel_month_12(self):
        # Month 12 시나리오: 방문 20K → 가입 2K (10%) → 체험 1.5K → 결제 100 → 갱신 90
        funnel = ConversionFunnel(
            visits=20_000, signups=2_000, trials=1_500, paid=100, renewed=90
        )
        assert funnel.signup_rate == 0.10
        assert funnel.trial_start_rate == 0.75
        assert funnel.paid_rate == pytest.approx(0.0667, abs=0.001)
        assert funnel.retention_rate == 0.90
        assert funnel.overall_paid_rate == 0.005

    def test_label_kr_format(self):
        funnel = ConversionFunnel(
            visits=1_000, signups=100, trials=80, paid=5, renewed=4
        )
        label = funnel.label_kr()
        assert "방문 1,000" in label
        assert "가입 100" in label
        assert "10.0%" in label

    def test_negative_count_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            ConversionFunnel(visits=-1, signups=0, trials=0, paid=0, renewed=0)

    def test_diagnose_zero_visits(self):
        funnel = ConversionFunnel(visits=0, signups=0, trials=0, paid=0, renewed=0)
        assert "방문 0" in diagnose_funnel(funnel)

    def test_diagnose_low_signup_rate(self):
        funnel = ConversionFunnel(
            visits=10_000, signups=200, trials=0, paid=0, renewed=0
        )  # 2%
        assert "가입율" in diagnose_funnel(funnel)

    def test_diagnose_low_paid_rate(self):
        funnel = ConversionFunnel(
            visits=10_000, signups=1_000, trials=800, paid=5, renewed=0
        )  # 0.625%
        assert "결제 전환율" in diagnose_funnel(funnel)

    def test_diagnose_low_retention(self):
        funnel = ConversionFunnel(
            visits=10_000, signups=1_000, trials=800, paid=50, renewed=20
        )  # 40%
        assert "갱신율" in diagnose_funnel(funnel)

    def test_diagnose_normal_range(self):
        funnel = ConversionFunnel(
            visits=10_000, signups=1_000, trials=700, paid=30, renewed=27
        )
        assert "정상" in diagnose_funnel(funnel)


class TestReferralCode:
    """Cycle 146: 추천 코드 (viral·growth helper)."""

    def test_format_matches(self):
        import re

        rid = generate_referral_code()
        assert re.match(r"^ref_[0-9a-f]{8}$", rid)

    def test_uniqueness_500(self):
        codes = {generate_referral_code() for _ in range(500)}
        assert len(codes) == 500

    def test_custom_prefix(self):
        code = generate_referral_code(prefix="invite")
        assert code.startswith("invite_")

    def test_invalid_prefix_rejected(self):
        with pytest.raises(ValueError, match="prefix"):
            generate_referral_code(prefix="")
        with pytest.raises(ValueError, match="prefix"):
            generate_referral_code(prefix="TOOLONG12")


class TestChurnRate:
    """Cycle 152: 월 churn rate (구독 SaaS 핵심 KPI)."""

    def test_zero_start_zero_rate(self):
        assert calculate_churn_rate(0, 0, 0) == 0.0

    def test_no_churn_growth_only(self):
        # Start 100·신규 +20·End 120 = churned 0
        rate = calculate_churn_rate(paid_start=100, paid_end=120, new_paid_in_period=20)
        assert rate == 0.0

    def test_5_percent_churn(self):
        # Start 100·신규 +10·End 105 = churned 5 → 5/100 = 5%
        rate = calculate_churn_rate(paid_start=100, paid_end=105, new_paid_in_period=10)
        assert rate == 0.05

    def test_high_churn_15_percent(self):
        # Start 100·신규 +20·End 105 = churned 15 → 15%
        rate = calculate_churn_rate(paid_start=100, paid_end=105, new_paid_in_period=20)
        assert rate == 0.15

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            calculate_churn_rate(-1, 0, 0)

    def test_no_negative_churn(self):
        # 음수 방지 (이상한 데이터·신규 미반영 등)
        rate = calculate_churn_rate(paid_start=10, paid_end=50, new_paid_in_period=5)
        assert rate == 0.0  # paid_end > start + new = 음수 = 0 클램프


class TestLtv:
    """Cycle 153: LTV·CAC·payback (구독 SaaS 핵심 KPI·VC 표준)."""

    def test_ltv_9900_5_percent_churn(self):
        # ARPU ₩9,900·5% churn → LTV ₩198,000
        ltv = calculate_ltv_krw(arpu_krw=9_900, monthly_churn_rate=0.05)
        assert ltv == 198_000

    def test_ltv_zero_churn_returns_zero(self):
        # churn 0 = 무한대·실 운영 = 미정 (0 반환)
        assert calculate_ltv_krw(arpu_krw=9_900, monthly_churn_rate=0.0) == 0

    def test_ltv_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            calculate_ltv_krw(arpu_krw=-100, monthly_churn_rate=0.05)


class TestLtvCacRatio:
    """LTV/CAC ≥ 3 = 정상 (Bessemer Cloud Index)."""

    def test_ratio_5x(self):
        # LTV ₩200K·CAC ₩40K = 5x (우수)
        ratio = calculate_ltv_cac_ratio(ltv_krw=200_000, cac_krw=40_000)
        assert ratio == 5.0

    def test_ratio_3x_normal(self):
        ratio = calculate_ltv_cac_ratio(ltv_krw=300_000, cac_krw=100_000)
        assert ratio == 3.0

    def test_zero_cac_returns_zero(self):
        # CAC 0 = 무한대·미정
        assert calculate_ltv_cac_ratio(ltv_krw=200_000, cac_krw=0) == 0.0

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            calculate_ltv_cac_ratio(ltv_krw=-1, cac_krw=10_000)


class TestPaybackMonths:
    """Payback ≤ 12개월 = 정상·≤ 6개월 = 우수."""

    def test_4_months(self):
        # CAC ₩40K·ARPU ₩9,900 = 4.04 개월
        payback = calculate_payback_months(cac_krw=40_000, arpu_krw=9_900)
        assert payback == 4.0

    def test_zero_arpu_returns_zero(self):
        assert calculate_payback_months(cac_krw=10_000, arpu_krw=0) == 0.0

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            calculate_payback_months(cac_krw=-1, arpu_krw=9_900)


class TestRuleOf40:
    """Cycle 159: Bessemer Rule of 40 (성장 + 마진 ≥ 40)."""

    def test_pass_30_growth_10_margin(self):
        result = calculate_rule_of_40(growth_rate_pct=30, profit_margin_pct=10)
        assert result["score"] == 40
        assert result["passes"] is True
        assert "정상" in result["label_kr"]

    def test_excellent_60(self):
        result = calculate_rule_of_40(growth_rate_pct=40, profit_margin_pct=20)
        assert result["score"] == 60
        assert "우수" in result["label_kr"]

    def test_below_threshold(self):
        result = calculate_rule_of_40(growth_rate_pct=10, profit_margin_pct=5)
        assert result["score"] == 15
        assert result["passes"] is False
        assert "위험" in result["label_kr"]

    def test_negative_margin_aggressive_growth(self):
        # 성장 50 + 마진 -5 = 45 (적자 단계 정상)
        result = calculate_rule_of_40(growth_rate_pct=50, profit_margin_pct=-5)
        assert result["score"] == 45
        assert result["passes"] is True

    def test_extreme_negative_rejected(self):
        with pytest.raises(ValueError, match="profit_margin_pct"):
            calculate_rule_of_40(growth_rate_pct=10, profit_margin_pct=-200)


class TestNrr:
    """Cycle 159: NRR (Net Revenue Retention)."""

    def test_100_percent_no_change(self):
        # 시작 ₩1M·expansion 100K·churn 100K → 100%
        nrr = calculate_nrr_pct(
            start_mrr_krw=1_000_000,
            expansion_krw=100_000,
            churn_krw=100_000,
        )
        assert nrr == 100.0

    def test_110_excellent(self):
        # 시작 ₩1M·expansion 200K·churn 100K → 110%
        nrr = calculate_nrr_pct(
            start_mrr_krw=1_000_000,
            expansion_krw=200_000,
            churn_krw=100_000,
        )
        assert nrr == 110.0

    def test_below_100_at_risk(self):
        nrr = calculate_nrr_pct(
            start_mrr_krw=1_000_000,
            expansion_krw=50_000,
            churn_krw=150_000,
        )
        assert nrr == 90.0

    def test_zero_start_returns_zero(self):
        nrr = calculate_nrr_pct(
            start_mrr_krw=0,
            expansion_krw=100_000,
            churn_krw=0,
        )
        assert nrr == 0.0

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            calculate_nrr_pct(
                start_mrr_krw=-1,
                expansion_krw=0,
                churn_krw=0,
            )


class TestDiagnoseNrr:
    """NRR 자동 진단."""

    def test_excellent(self):
        assert "우수" in diagnose_nrr(115.0)

    def test_normal(self):
        assert "정상" in diagnose_nrr(105.0)

    def test_warning(self):
        assert "보통" in diagnose_nrr(95.0)

    def test_dangerous(self):
        assert "위험" in diagnose_nrr(80.0)


class TestBessemerSummary:
    """Cycle 160: Bessemer 5 KPI 한 줄 요약 (PO 매주 알림)."""

    def test_all_pass(self):
        # #31 Pro 시나리오: 모든 임계값 통과
        summary = format_bessemer_summary_kr(
            ltv_krw=198_000,
            ltv_cac_ratio=4.95,
            payback_months=4.0,
            rule_of_40_score=80,
            nrr_pct=110,
        )
        assert "✅" in summary
        assert "❌" not in summary
        assert "₩198,000" in summary
        assert "R40 80" in summary
        assert "NRR 110%" in summary

    def test_low_ltv_warning(self):
        summary = format_bessemer_summary_kr(
            ltv_krw=10_000,  # < ₩50K
            ltv_cac_ratio=4.95,
            payback_months=4.0,
            rule_of_40_score=80,
            nrr_pct=110,
        )
        assert "⚠ LTV ₩10,000" in summary

    def test_low_ltv_cac_critical(self):
        summary = format_bessemer_summary_kr(
            ltv_krw=100_000,
            ltv_cac_ratio=1.5,  # < 3
            payback_months=4.0,
            rule_of_40_score=80,
            nrr_pct=110,
        )
        assert "❌ LTV/CAC 1.5" in summary

    def test_dangerous_nrr(self):
        summary = format_bessemer_summary_kr(
            ltv_krw=100_000,
            ltv_cac_ratio=3.5,
            payback_months=8.0,
            rule_of_40_score=45,
            nrr_pct=80,  # < 90
        )
        assert "❌ NRR 80%" in summary

    def test_format_separator(self):
        summary = format_bessemer_summary_kr(
            ltv_krw=100_000,
            ltv_cac_ratio=3.0,
            payback_months=10.0,
            rule_of_40_score=45,
            nrr_pct=100,
        )
        # 5 KPI · 4 separator
        assert summary.count("·") == 4


class TestArpu:
    """Cycle 164: ARPU (Average Revenue Per User)."""

    def test_31_single_plan(self):
        # #31 100명 결제·₩990K 매출 → ARPU ₩9,900
        arpu = calculate_arpu_krw(monthly_revenue_krw=990_000, paying_users=100)
        assert arpu == 9_900

    def test_32_single_plan(self):
        arpu = calculate_arpu_krw(monthly_revenue_krw=490_000, paying_users=100)
        assert arpu == 4_900

    def test_zero_users_returns_zero(self):
        assert calculate_arpu_krw(monthly_revenue_krw=100_000, paying_users=0) == 0

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            calculate_arpu_krw(monthly_revenue_krw=-1, paying_users=10)


class TestMrrGrowth:
    """Cycle 166: 월 MRR 성장률."""

    def test_20_percent_growth(self):
        # ₩1M → ₩1.2M = 20%
        rate = calculate_mrr_growth_pct(
            previous_mrr_krw=1_000_000, current_mrr_krw=1_200_000
        )
        assert rate == 20.0

    def test_decline_negative(self):
        rate = calculate_mrr_growth_pct(
            previous_mrr_krw=1_000_000, current_mrr_krw=900_000
        )
        assert rate == -10.0

    def test_zero_previous_returns_zero(self):
        rate = calculate_mrr_growth_pct(
            previous_mrr_krw=0, current_mrr_krw=100_000
        )
        assert rate == 0.0

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            calculate_mrr_growth_pct(previous_mrr_krw=-1, current_mrr_krw=0)


class TestGrowthSummary:
    """Cycle 167: 성장·churn·NRR 한 줄 요약."""

    def test_all_pass(self):
        summary = format_growth_summary_kr(
            mrr_growth_pct=15.0,
            churn_pct=4.0,
            nrr_pct=110,
        )
        assert "✅" in summary
        assert "❌" not in summary
        assert "+15.0%" in summary
        assert "4.0%" in summary
        assert "110.0%" in summary

    def test_decline_growth(self):
        summary = format_growth_summary_kr(
            mrr_growth_pct=-5.0,
            churn_pct=4.0,
            nrr_pct=110,
        )
        assert "❌ 성장 -5.0%" in summary

    def test_high_churn_critical(self):
        summary = format_growth_summary_kr(
            mrr_growth_pct=10.0,
            churn_pct=15.0,
            nrr_pct=100,
        )
        assert "❌ churn 15.0%" in summary

    def test_dangerous_nrr(self):
        summary = format_growth_summary_kr(
            mrr_growth_pct=10.0,
            churn_pct=5.0,
            nrr_pct=80.0,
        )
        assert "❌ NRR 80.0%" in summary
