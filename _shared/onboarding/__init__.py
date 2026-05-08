"""온보딩 모듈 (Cycle 124·신규).

체험 카운터·Founding 100명 슬롯·매출 마일스톤 트래커.
#31·#32 외부 발사 시 즉시 사용 가능 (Streamlit 통합).

3 클래스:
- TrialCounter: 14일 무료 체험 남은 일수·종료 임박 알림
- FoundingSlotTracker: Founding Member 100명 슬롯·잔여·Sold-out
- MilestoneTracker: Month 1·6·12 매출 마일스톤 (Habit Pixel 벤치마크)
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta


@dataclass(frozen=True)
class TrialStatus:
    days_remaining: int
    is_expired: bool
    is_warning: bool  # 3일 이하 = warning
    label_kr: str


def calculate_trial_status(
    started_at: datetime,
    trial_days: int = 14,
    now: datetime | None = None,
) -> TrialStatus:
    """체험 기간 계산.

    Args:
        started_at: 가입 시점 (UTC tzinfo 의무)
        trial_days: 체험 일수 (기본 14·외부 901 진단 정합)
        now: 현재 시점 (테스트용·기본 = UTC now)
    """
    if started_at.tzinfo is None:
        msg = "started_at = UTC tzinfo 의무 (헌법 §3)"
        raise ValueError(msg)
    current = now or datetime.now(UTC)
    elapsed = (current - started_at).days
    remaining = max(0, trial_days - elapsed)
    expired = remaining == 0
    warning = 0 < remaining <= 3
    if expired:
        label = "체험 종료·결제 시 계속 사용 가능"
    elif warning:
        label = f"체험 {remaining}일 남음·곧 종료"
    else:
        label = f"체험 {remaining}일 남음"
    return TrialStatus(
        days_remaining=remaining,
        is_expired=expired,
        is_warning=warning,
        label_kr=label,
    )


@dataclass(frozen=True)
class FoundingSlot:
    total: int
    taken: int
    remaining: int
    is_sold_out: bool
    label_kr: str
    discount_percent: int  # 50% (영구)


def calculate_founding_slot(
    taken: int,
    total: int = 100,
    discount_percent: int = 50,
) -> FoundingSlot:
    """Founding Member 슬롯 계산.

    영구 50% 할인·100명 한정 (외부 901 진단 정합·Pieter Levels 패턴).
    """
    if taken < 0 or total <= 0:
        msg = "taken ≥ 0·total > 0 의무"
        raise ValueError(msg)
    capped = min(taken, total)
    remaining = total - capped
    sold_out = remaining == 0
    if sold_out:
        label = f"Founding Member 마감 ({total}명 한정)"
    else:
        label = f"Founding Member {remaining}/{total} 잔여·영구 {discount_percent}% 할인"
    return FoundingSlot(
        total=total,
        taken=capped,
        remaining=remaining,
        is_sold_out=sold_out,
        label_kr=label,
        discount_percent=discount_percent,
    )


@dataclass(frozen=True)
class Milestone:
    month: int  # 1·6·12
    target_users: int
    target_paying: int
    target_mrr_krw: int
    label_kr: str


# Habit Pixel 벤치마크 (외부 901 진단·ADR 0058 정합)
DEFAULT_MILESTONES: tuple[Milestone, ...] = (
    Milestone(
        month=1,
        target_users=100,
        target_paying=3,
        target_mrr_krw=29_700,
        label_kr="Month 1: 가입 100·결제 3·MRR ₩29,700",
    ),
    Milestone(
        month=6,
        target_users=500,
        target_paying=25,
        target_mrr_krw=247_500,
        label_kr="Month 6: 가입 500·결제 25·MRR ₩247,500",
    ),
    Milestone(
        month=12,
        target_users=2_000,
        target_paying=100,
        target_mrr_krw=990_000,
        label_kr="Month 12: 가입 2,000·결제 100·MRR ₩990,000 ≈ $750",
    ),
)


def get_current_milestone(
    months_since_launch: int,
    milestones: tuple[Milestone, ...] = DEFAULT_MILESTONES,
) -> Milestone:
    """현재 시점에 가장 가까운 다음 마일스톤 반환."""
    if months_since_launch < 0:
        msg = "months_since_launch ≥ 0 의무"
        raise ValueError(msg)
    for m in milestones:
        if months_since_launch < m.month:
            return m
    return milestones[-1]


def calculate_progress_percent(
    actual_paying: int,
    milestone: Milestone,
) -> int:
    """현재 실제 결제 사용자 vs 마일스톤 목표 진척도 (%)."""
    if milestone.target_paying == 0:
        return 0
    return min(100, int(actual_paying / milestone.target_paying * 100))


@dataclass(frozen=True)
class ConversionFunnel:
    """5 단계 전환 funnel KPI (외부 발사 후 운영 KPI).

    벤치마크 (외부 901 진단 + Habit Pixel):
    - signup_rate: visit → signup ≈ 8~15% (옵트인 전환)
    - trial_start_rate: signup → trial ≈ 60~80%
    - paid_rate: trial → paid ≈ 3~7% (Habit Pixel 5%)
    - retention_rate: paid → renewed ≈ 80~95% (구독 SaaS)
    """

    visits: int
    signups: int
    trials: int
    paid: int
    renewed: int

    def __post_init__(self) -> None:
        for n in (self.visits, self.signups, self.trials, self.paid, self.renewed):
            if n < 0:
                msg = "단계 수치 ≥ 0 의무"
                raise ValueError(msg)

    @property
    def signup_rate(self) -> float:
        if self.visits == 0:
            return 0.0
        return round(self.signups / self.visits, 4)

    @property
    def trial_start_rate(self) -> float:
        if self.signups == 0:
            return 0.0
        return round(self.trials / self.signups, 4)

    @property
    def paid_rate(self) -> float:
        if self.trials == 0:
            return 0.0
        return round(self.paid / self.trials, 4)

    @property
    def retention_rate(self) -> float:
        if self.paid == 0:
            return 0.0
        return round(self.renewed / self.paid, 4)

    @property
    def overall_paid_rate(self) -> float:
        """visit → paid 종합 전환 (마케팅 funnel KPI)."""
        if self.visits == 0:
            return 0.0
        return round(self.paid / self.visits, 4)

    def label_kr(self) -> str:
        """대시보드 한 줄 요약 (Streamlit caption·이메일 hero)."""
        return (
            f"방문 {self.visits:,} → 가입 {self.signups:,} ({self.signup_rate:.1%})"
            f" → 체험 {self.trials:,} ({self.trial_start_rate:.1%})"
            f" → 결제 {self.paid:,} ({self.paid_rate:.1%})"
            f" → 갱신 {self.renewed:,} ({self.retention_rate:.1%})"
            f" / 종합 {self.overall_paid_rate:.2%}"
        )


def generate_referral_code(prefix: str = "ref") -> str:
    """추천 코드 생성 (viral·growth helper).

    형식: {prefix}_{8자 hex} = 짧고 입력 가능 (이메일·SMS·QR)
    예: ref_a4b7c1d9
    """
    if not prefix or len(prefix) > 8:
        msg = "prefix = 1~8자 의무"
        raise ValueError(msg)
    return f"{prefix}_{secrets.token_hex(4)}"


def calculate_mrr_growth_pct(
    previous_mrr_krw: int,
    current_mrr_krw: int,
) -> float:
    """월 MRR 성장률 (% 단위·Bessemer 정합).

    벤치마크 (외부 901 + Habit Pixel):
        - 10~20% = early stage 정상
        - 5~10% = mid stage
        - 1~5% = mature
    """
    if previous_mrr_krw < 0 or current_mrr_krw < 0:
        msg = "MRR ≥ 0 의무"
        raise ValueError(msg)
    if previous_mrr_krw == 0:
        return 0.0  # 신규 시작 = 무한대·미정
    return round((current_mrr_krw - previous_mrr_krw) / previous_mrr_krw * 100, 1)


def calculate_arpu_krw(
    monthly_revenue_krw: int,
    paying_users: int,
) -> int:
    """ARPU 계산 (Average Revenue Per User·LTV·Bessemer 정합).

    공식: ARPU = 월 매출 / 결제 사용자
    벤치마크 (외부 901):
        - #31 ₩9,900 정액 = ARPU ₩9,900 (단일 플랜)
        - #32 ₩4,900 정액 = ARPU ₩4,900
        - 다중 플랜 (Free·Pro·Founding) = 가중 평균
    """
    if monthly_revenue_krw < 0 or paying_users < 0:
        msg = "monthly_revenue·paying_users ≥ 0 의무"
        raise ValueError(msg)
    if paying_users == 0:
        return 0
    return monthly_revenue_krw // paying_users


def calculate_rule_of_40(
    growth_rate_pct: float,
    profit_margin_pct: float,
) -> dict[str, float | str]:
    """Rule of 40 (Bessemer Cloud Index·SaaS finance 표준).

    공식: 성장률(%) + 영업이익률(%) ≥ 40 = 정상
    예: 성장 30 + 마진 10 = 40 ✅
    예: 성장 50 + 마진 -10 = 40 (적자 단계 정상)

    Args:
        growth_rate_pct: 연 매출 성장률 (% 단위·30 = 30%)
        profit_margin_pct: 영업이익률 (% 단위·-100~100)

    Returns:
        dict: score·passes·label_kr (Streamlit·이메일 통합)
    """
    if profit_margin_pct < -100:
        msg = "profit_margin_pct ≥ -100 의무"
        raise ValueError(msg)
    score = round(growth_rate_pct + profit_margin_pct, 1)
    passes = score >= 40
    if score >= 60:
        label = f"우수 ({score:.1f}·SaaS 표준 60+)"
    elif score >= 40:
        label = f"정상 ({score:.1f}·≥40 통과)"
    elif score >= 20:
        label = f"보통 ({score:.1f}·40 미달·개선 필요)"
    else:
        label = f"위험 ({score:.1f}·재검토 의무)"
    return {
        "score": score,
        "passes": passes,
        "label_kr": label,
    }


def calculate_nrr_pct(
    start_mrr_krw: int,
    expansion_krw: int,
    churn_krw: int,
    downgrade_krw: int = 0,
) -> float:
    """Net Revenue Retention 계산 (구독 SaaS 핵심·Bessemer 정합).

    공식: NRR = (start + expansion - churn - downgrade) / start × 100

    벤치마크 (외부 901 진단):
        - NRR ≥ 110% = 우수 (expansion·upsell)
        - NRR 100~110% = 정상
        - NRR < 100% = churn 위험 (즉시 개선)
    """
    if start_mrr_krw < 0 or expansion_krw < 0 or churn_krw < 0 or downgrade_krw < 0:
        msg = "모든 금액 ≥ 0 의무"
        raise ValueError(msg)
    if start_mrr_krw == 0:
        return 0.0
    end_mrr = start_mrr_krw + expansion_krw - churn_krw - downgrade_krw
    return round(end_mrr / start_mrr_krw * 100, 1)


def format_growth_summary_kr(
    mrr_growth_pct: float,
    churn_pct: float,
    nrr_pct: float,
) -> str:
    """성장률·churn·NRR 한 줄 요약 (자동 진단·아이콘).

    벤치마크 (Bessemer + 외부 901):
        - mrr_growth ≥ 10% (early)·≥ 5% (mid)·≥ 1% (mature)
        - churn ≤ 10% (B2C)·≤ 3% (B2B)
        - NRR ≥ 100·≥ 110 우수
    """
    # 성장률
    if mrr_growth_pct >= 10:
        g_icon = "✅"
    elif mrr_growth_pct >= 5:
        g_icon = "✅"
    elif mrr_growth_pct >= 0:
        g_icon = "⚠"
    else:
        g_icon = "❌"
    # churn
    if churn_pct <= 5:
        c_icon = "✅"
    elif churn_pct <= 10:
        c_icon = "⚠"
    else:
        c_icon = "❌"
    # NRR
    if nrr_pct >= 110:
        n_icon = "✅"
    elif nrr_pct >= 100:
        n_icon = "✅"
    elif nrr_pct >= 90:
        n_icon = "⚠"
    else:
        n_icon = "❌"
    return (
        f"{g_icon} 성장 {mrr_growth_pct:+.1f}% · "
        f"{c_icon} churn {churn_pct:.1f}% · "
        f"{n_icon} NRR {nrr_pct:.1f}%"
    )


def format_bessemer_summary_kr(
    ltv_krw: int,
    ltv_cac_ratio: float,
    payback_months: float,
    rule_of_40_score: float,
    nrr_pct: float,
) -> str:
    """Bessemer Cloud Index 5 KPI 한 줄 한국어 요약.

    매주 PO 알림 통합 (build_weekly_kpi_message 페어·Cycle 142 정합).
    임계값 자동 표시 (✅ 통과·⚠ 경고·❌ 위험).
    """
    parts: list[str] = []
    # LTV (≥ ₩50K 정상)
    ltv_icon = "✅" if ltv_krw >= 50_000 else "⚠"
    parts.append(f"{ltv_icon} LTV ₩{ltv_krw:,}")
    # LTV/CAC (≥ 3 정상·≥ 5 우수)
    if ltv_cac_ratio >= 5:
        cac_icon = "✅"
    elif ltv_cac_ratio >= 3:
        cac_icon = "✅"
    else:
        cac_icon = "❌"
    parts.append(f"{cac_icon} LTV/CAC {ltv_cac_ratio}")
    # Payback (≤ 6 우수·≤ 12 정상)
    if payback_months <= 6:
        pb_icon = "✅"
    elif payback_months <= 12:
        pb_icon = "✅"
    else:
        pb_icon = "⚠"
    parts.append(f"{pb_icon} Payback {payback_months}월")
    # Rule of 40 (≥ 60 우수·≥ 40 정상)
    if rule_of_40_score >= 60:
        r40_icon = "✅"
    elif rule_of_40_score >= 40:
        r40_icon = "✅"
    elif rule_of_40_score >= 20:
        r40_icon = "⚠"
    else:
        r40_icon = "❌"
    parts.append(f"{r40_icon} R40 {rule_of_40_score}")
    # NRR (≥ 110 우수·≥ 100 정상)
    if nrr_pct >= 110:
        nrr_icon = "✅"
    elif nrr_pct >= 100:
        nrr_icon = "✅"
    elif nrr_pct >= 90:
        nrr_icon = "⚠"
    else:
        nrr_icon = "❌"
    parts.append(f"{nrr_icon} NRR {nrr_pct}%")
    return " · ".join(parts)


def diagnose_nrr(nrr_pct: float) -> str:
    """NRR 진단 (Streamlit·이메일·자동 alert)."""
    if nrr_pct >= 110:
        return f"우수 ({nrr_pct}%·expansion·upsell 강력)"
    if nrr_pct >= 100:
        return f"정상 ({nrr_pct}%·유지·확장 시작)"
    if nrr_pct >= 90:
        return f"보통 ({nrr_pct}%·churn 위험·개선 필요)"
    return f"위험 ({nrr_pct}%·즉시 개선·매출 감소)"


def calculate_ltv_krw(
    arpu_krw: int,
    monthly_churn_rate: float,
) -> int:
    """LTV (Lifetime Value) 계산 (구독 SaaS 표준).

    공식: LTV = ARPU / churn_rate (단순)·ARPU × (1 / churn) = 평생 가치.
    벤치마크 (외부 901 + Habit Pixel·VC 표준):
        - LTV ≥ ₩50,000 = 정상 (#31 ₩9,900·5% churn = ₩198,000)
        - LTV/CAC ≥ 3 = 정상 (Bessemer Cloud Index)

    Args:
        arpu_krw: ARPU = 결제 1인당 월 매출 (Average Revenue Per User)
        monthly_churn_rate: 월 churn (0.05 = 5%)
    """
    if arpu_krw < 0 or monthly_churn_rate < 0:
        msg = "arpu·churn ≥ 0 의무"
        raise ValueError(msg)
    if monthly_churn_rate == 0:
        return 0  # churn 0 = 무한대·실 운영 = LTV 미정 (호출자 결정)
    return int(arpu_krw / monthly_churn_rate)


def calculate_ltv_cac_ratio(
    ltv_krw: int,
    cac_krw: int,
) -> float:
    """LTV/CAC ratio (Bessemer Cloud Index·≥3 정상)."""
    if ltv_krw < 0 or cac_krw < 0:
        msg = "ltv·cac ≥ 0 의무"
        raise ValueError(msg)
    if cac_krw == 0:
        return 0.0  # CAC 0 = 무한대·실 운영 = 미정
    return round(ltv_krw / cac_krw, 2)


def calculate_payback_months(
    cac_krw: int,
    arpu_krw: int,
) -> float:
    """Payback period (CAC 회수 개월·구독 SaaS 표준).

    공식: payback = CAC / ARPU (월)
    벤치마크: ≤ 12개월 = 정상·≤ 6개월 = 우수 (Bessemer).
    """
    if cac_krw < 0 or arpu_krw < 0:
        msg = "cac·arpu ≥ 0 의무"
        raise ValueError(msg)
    if arpu_krw == 0:
        return 0.0
    return round(cac_krw / arpu_krw, 1)


def calculate_churn_rate(
    paid_start: int,
    paid_end: int,
    new_paid_in_period: int,
) -> float:
    """월 churn rate 계산 (구독 SaaS 핵심 KPI).

    공식 (구독 SaaS 표준):
        churned = paid_start + new - paid_end
        churn_rate = churned / paid_start

    벤치마크 (외부 901 진단 + Habit Pixel):
        - B2C 구독 = 월 5~10% (정상)
        - B2B 구독 = 월 1~3% (정상)
        - 위험 = 월 15%+ (즉시 개선)
    """
    if paid_start < 0 or paid_end < 0 or new_paid_in_period < 0:
        msg = "paid_start·paid_end·new_paid ≥ 0 의무"
        raise ValueError(msg)
    if paid_start == 0:
        return 0.0
    churned = max(0, paid_start + new_paid_in_period - paid_end)
    return round(churned / paid_start, 4)


def diagnose_funnel(funnel: ConversionFunnel) -> str:
    """funnel 약점 진단 (자동·다음 cycle 개선 영역 탐지)."""
    if funnel.visits == 0:
        return "방문 0 = 마케팅·SEO 우선 (외부 발사 직후 정상)"
    if funnel.signup_rate < 0.05:
        return "가입율 < 5% = 랜딩 메시지·CTA 약함 (8~15% 목표)"
    if funnel.signups > 0 and funnel.trial_start_rate < 0.40:
        return "체험 시작율 < 40% = onboarding UX 개선 (60~80% 목표)"
    if funnel.trials > 0 and funnel.paid_rate < 0.02:
        return "결제 전환율 < 2% = 가격·가치 메시지 약함 (3~7% 목표)"
    if funnel.paid > 0 and funnel.retention_rate < 0.70:
        return "갱신율 < 70% = churn 높음 (80~95% 목표)"
    return "정상 범위 (모든 단계 벤치마크 도달)"


def format_pricing_summary_kr(
    monthly_price_krw: int,
    founding_slot: FoundingSlot,
    trial_days: int = 14,
) -> str:
    """가격 + Founding + 체험 한 줄 한국어 요약 (Streamlit caption·이메일 hero)."""
    if monthly_price_krw < 0 or trial_days < 0:
        msg = "monthly_price_krw·trial_days ≥ 0 의무"
        raise ValueError(msg)
    if founding_slot.is_sold_out:
        return f"₩{monthly_price_krw:,}/월·{trial_days}일 무료 체험 (Founding 마감)"
    discounted = monthly_price_krw * (100 - founding_slot.discount_percent) // 100
    return (
        f"Founding ₩{discounted:,}/월 (영구 {founding_slot.discount_percent}%·"
        f"{founding_slot.remaining}/{founding_slot.total} 잔여)·"
        f"{trial_days}일 무료 체험"
    )


__all__ = [
    "DEFAULT_MILESTONES",
    "ConversionFunnel",
    "FoundingSlot",
    "Milestone",
    "TrialStatus",
    "calculate_arpu_krw",
    "calculate_churn_rate",
    "calculate_founding_slot",
    "calculate_ltv_cac_ratio",
    "calculate_ltv_krw",
    "calculate_mrr_growth_pct",
    "calculate_nrr_pct",
    "calculate_payback_months",
    "calculate_rule_of_40",
    "calculate_progress_percent",
    "calculate_trial_status",
    "diagnose_funnel",
    "diagnose_nrr",
    "format_bessemer_summary_kr",
    "format_growth_summary_kr",
    "format_pricing_summary_kr",
    "generate_referral_code",
    "get_current_milestone",
]
