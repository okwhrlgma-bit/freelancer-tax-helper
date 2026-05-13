"""freelancer-tax-helper Streamlit UI — 한국 프리랜서 종소세 환급 추정.

ADR 0058 배포 가능 (시장 90·캐시카우 100·벤치마크 삼쩜삼·Q5 PASS).
삼쩜삼 변형 (정액제 ₩9,900/월·offline·MIT).
헌법 §14 (offline·session_state)·§11 (카테고리)·§12 (KWCAG).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
# _shared 경로 등록 (Cycle 168 분리·local sub-package·외부 GitHub repo 정합)
sys.path.insert(0, str(Path(__file__).parent / "_shared"))

import streamlit as st  # type: ignore[import-not-found]

from freelancer_tax_helper import Receipt, analyze, auto_categorize_receipts
from freelancer_tax_helper.categories import CATEGORIES
from freelancer_tax_helper.refund import SIMPLE_RATE

# _shared/landing 컴포넌트 (Cycle 119 신규 3건 추가·합 7 컴포넌트)
try:
    from landing.streamlit_helper import (
        render_benchmark_section,
        render_cta_bar,
        render_disclaimer_footer,
        render_features_comparison,
        render_founder_story,
        render_onboarding_bar,
        render_persona_match,
        render_pricing_grid,
    )

    SHARED_LANDING_AVAILABLE = True
except ImportError:
    SHARED_LANDING_AVAILABLE = False

# _shared/onboarding (Cycle 124 신규·14일 체험·Founding 100·매출 마일스톤)
try:
    from onboarding import (
        calculate_founding_slot,
        calculate_trial_status,
        get_current_milestone,
    )

    SHARED_ONBOARDING_AVAILABLE = True
except ImportError:
    SHARED_ONBOARDING_AVAILABLE = False

# Agent G·Cycle 1362·일괄 1·_shared 핵심 모듈 강제 import (신규 배선)
try:
    from payments import calculate_fees, verify_payment_amount  # type: ignore[import-not-found]
    from auth import (  # type: ignore[import-not-found]
        AuditChain,
        LoginRateLimiter,
        mask_email_for_display,
        validate_password_strength,
    )
    from email_helper import build_receipt_message  # type: ignore[import-not-found]

    SHARED_CORE_AVAILABLE = True
except ImportError as _shared_import_err:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "_shared 핵심 모듈 일부 로드 실패 (degraded mode): %s", _shared_import_err
    )
    SHARED_CORE_AVAILABLE = False

# Agent G·Cycle 1362·일괄 4·Sentry init (env SENTRY_DSN 설정 시만)
_SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if _SENTRY_DSN:
    try:
        import sentry_sdk  # type: ignore[import-not-found]

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=os.environ.get("ENV", "production"),
            release=os.environ.get("RELEASE", "v0.1.0"),
        )
    except ImportError:
        pass  # sentry_sdk 미설치·degraded mode

# Agent G·Cycle 1362·일괄 5·analytics (PostHog 옵션·GA4 = landing/index.html 측)
_POSTHOG_KEY = os.environ.get("POSTHOG_API_KEY", "")
try:
    if _POSTHOG_KEY:
        import posthog  # type: ignore[import-not-found]
        posthog.api_key = _POSTHOG_KEY
        POSTHOG_AVAILABLE = True
    else:
        POSTHOG_AVAILABLE = False
except ImportError:
    POSTHOG_AVAILABLE = False


def track_event(event_name: str, properties: dict | None = None, distinct_id: str = "anonymous") -> None:
    """analytics 이벤트 트래킹 (PostHog·env 미설정 시 no-op)."""
    if not POSTHOG_AVAILABLE:
        return
    try:
        posthog.capture(distinct_id, event_name, properties or {})  # type: ignore[name-defined]
    except Exception:  # noqa: BLE001 (분석 실패 = UX 영향 X)
        pass


st.set_page_config(
    page_title="프리랜서 종소세 환급 계산기·단순경비율·삼쩜삼 변형·MIT",
    page_icon="💼",
    layout="centered",
    menu_items={
        "About": (
            "프리랜서 종소세 환급 추정기·디자이너·개발자·번역가·강사·작가·"
            "유튜버·블로거·외주 등 사업소득자·5월 종합소득세 신고 대비·"
            "단순경비율 vs 직접 비용 자동 비교·offline·MIT·헌법 §14."
        ),
    },
)

st.markdown(
    """
    # 💼 프리랜서 종소세 환급 추정기

    **단순경비율 vs 직접 비용 자동 비교·매월 영수증 정리·환급 미리 계산**

    > 한국 사업소득자 (3.3% 원천공제)·5월 종소세 신고 대비
    > 데이터 = 사용자 컴퓨터·외부 서버 X (헌법 §14)
    """
)

st.divider()

# 가격 그리드 + 비교 + CTA (Cycle 120 통합·_shared/landing)
if SHARED_LANDING_AVAILABLE:
    with st.expander("💰 가격·시작하기 (펼치기)"):
        # Founding 100 슬롯 + 체험 14일 (Cycle 133 render_onboarding_bar 단축)
        if SHARED_ONBOARDING_AVAILABLE:
            slot = calculate_founding_slot(taken=0)  # 발사 전 = 0
            milestone = get_current_milestone(0)
            render_onboarding_bar(slot.label_kr, milestone.label_kr)
        if render_cta_bar(
            "🚀 14일 무료 체험 시작",
            sublabel="가입 X·즉시 사용·결제 = PortOne 활성 시 (PO 결정 시)",
        ):
            # 모의 체험 활성 (session_state·offline·결제 없음)
            if "trial_started" not in st.session_state:
                st.session_state.trial_started = True
                st.session_state.trial_start_date = datetime.now().isoformat()
                expire = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
                st.success(
                    f"✅ 14일 무료 체험이 시작되었습니다. 만료일: {expire}·"
                    f"기능 100% 사용 가능·결제 X·계정 가입 X."
                )
            else:
                start = datetime.fromisoformat(st.session_state.trial_start_date)
                expire = (start + timedelta(days=14)).strftime("%Y-%m-%d")
                st.info(f"이미 체험 중입니다. 만료일: {expire}")
        render_pricing_grid([
            {
                "name": "Free",
                "price_krw": 0,
                "features": ["50 영수증/월", "기본 단순경비율", "MIT 무료"],
                "cta": "무료 시작",
            },
            {
                "name": "Pro",
                "price_krw": 9_900,
                "features": ["무제한 영수증", "AI 자동 분류 (BYOK)", "월간 PDF"],
                "recommended": True,
                "cta": "Pro 14일 무료",
            },
            {
                "name": "Founding 50%",
                "price_krw": 4_950,
                "features": ["Pro 기능 영구 50%", "100명 한정", "~2026-06-30"],
                "cta": "Founding 시작",
            },
        ])
        render_features_comparison([
            {"기능": "데이터 위치", "우리": "사용자 컴퓨터 (헌법 §14)", "삼쩜삼": "서버"},
            {"기능": "가격 모델", "우리": "정액 ₩9,900/월", "삼쩜삼": "환급액 18.7%"},
            {"기능": "라이선스", "우리": "MIT (오픈)", "삼쩜삼": "비공개"},
            {"기능": "offline", "우리": "✅", "삼쩜삼": "❌"},
        ])

# session_state
if "receipts" not in st.session_state:
    st.session_state.receipts = []

# 수입·사업코드 입력
col1, col2 = st.columns(2)
with col1:
    income = st.number_input(
        "연 수입 (원·원천공제 전 총액)",
        min_value=0,
        value=30_000_000,
        step=1_000_000,
        format="%d",
    )
with col2:
    business_code = st.selectbox(
        "사업코드",
        options=list(SIMPLE_RATE.keys()),
        format_func=lambda c: {
            "940100": "940100 IT 개발자 (67.6%)",
            "940200": "940200 디자인 (64.2%)",
            "940300": "940300 작가·번역 (58.7%)",
            "940500": "940500 컨설팅 (65.8%)",
            "940600": "940600 사진·영상 (61.2%)",
            "940904": "940904 작가 (58.7%)",
            "940906": "940906 강사·번역 (64.1%)",
            "940909": "940909 기타 자영업 (64.1%)",
        }.get(c, c),
    )

st.divider()

# 영수증 입력
with st.form("add_receipt"):
    st.subheader("🧾 영수증 추가")
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("날짜")
        amount = st.number_input("금액 (원)", min_value=1, value=10_000, step=1_000)
    with col2:
        vendor = st.text_input("vendor (가게·서비스 명)", placeholder="예: 스타벅스")
        category = st.selectbox(
            "카테고리",
            options=["other", *list(CATEGORIES.keys())],
            format_func=lambda c: f"{c} — {CATEGORIES.get(c, '미정')}",
        )

    submitted = st.form_submit_button("✅ 영수증 추가", type="primary")

if submitted and vendor:
    try:
        r = Receipt(
            date=date.isoformat(),
            amount=int(amount),
            vendor=vendor,
            category=category,
        )
        st.session_state.receipts.append(r)
        st.success(f"✅ 추가: {r.vendor} ₩{r.amount:,} ({r.category})")
    except ValueError as e:
        # 사용자에게 친절한 한국어 메시지·내부 상세는 로그
        st.error(
            "⚠️ 영수증 입력이 잘못됐습니다. 금액·날짜·가게명을 다시 확인해주세요."
        )
        import logging

        logging.warning("receipt validation failed: %s", e)
    except Exception:
        st.error("⚠️ 오류가 발생했습니다. 다시 시도해주세요.")
        import logging

        logging.exception("unexpected receipt error")

# 자동 분류 옵션
if st.session_state.receipts and st.button("🤖 vendor → 카테고리 자동 분류"):
    st.session_state.receipts = auto_categorize_receipts(st.session_state.receipts)
    st.rerun()

st.divider()

# 분석
if st.session_state.receipts:
    st.subheader(f"📊 분석 결과 (영수증 {len(st.session_state.receipts)}건)")

    report = analyze(st.session_state.receipts, int(income), business_code)

    # 핵심 메트릭
    col1, col2, col3 = st.columns(3)
    col1.metric("원천공제 (3.3%)", f"₩{report.withholding_total:,}")
    col2.metric("인정 비용 합계", f"₩{report.deductible_total:,}")

    refund = report.refund_estimate
    if refund > 0:
        col3.metric("환급 예상", f"₩{refund:,}", delta="환급")
    else:
        col3.metric("추가 납부", f"₩{abs(refund):,}", delta=f"-₩{abs(refund):,}")

    # 비용 비교
    st.subheader("📊 비용 비교 (둘 중 큰 값 적용)")
    cmp = report.simple_rate_comparison
    col1, col2 = st.columns(2)
    col1.metric("직접 비용", f"₩{cmp['direct_cost']:,}")
    col2.metric(
        f"단순경비율 ({SIMPLE_RATE[business_code]:.1%})",
        f"₩{cmp['simple_rate_cost']:,}",
    )

    if cmp["simple_rate_cost"] > cmp["direct_cost"]:
        st.info("💡 단순경비율 적용 유리·영수증 부담 X")
    else:
        st.info("💡 직접 비용 신고 유리·영수증 정리 ROI ↑")

    # 카테고리 별
    with st.expander("📂 카테고리별 인정 비용"):
        for cat, amount in report.category_breakdown.items():
            if amount > 0:
                st.markdown(f"- **{cat}** — {CATEGORIES[cat]}: ₩{amount:,}")

    # 경고·권고
    if report.missing_warnings:
        st.warning("\n".join(report.missing_warnings))

    st.subheader("📝 권고")
    for rec in report.recommendations:
        st.markdown(f"- {rec}")

    if st.button("🗑️ 모든 영수증 초기화"):
        st.session_state.receipts = []
        st.rerun()
else:
    st.info("🧾 위 폼에서 영수증을 추가하면 환급 추정이 시작됩니다.")

st.divider()

# _shared/landing 통합 (Cycle 110·신규 컴포넌트 추가)
if SHARED_LANDING_AVAILABLE:
    render_persona_match([
        {
            "title_ko": "💼 한국 프리랜서 (Tier 1·핵심)",
            "description_ko": "IT·디자인·작가·강사·번역·컨설팅·사진 = 사업소득자 3.3% 원천공제·5월 종소세",
            "fit_score": "✅ 결제권자 = 결제자 일치·시장 50만+",
        },
        {
            "title_ko": "🏢 1인 사업자 (확장)",
            "description_ko": "단순경비율 8 사업코드·누진세율 자동·세금계산서 X (홈택스 직접)",
            "fit_score": "🟡 부가세 신고 (확장 가능)",
        },
    ])
    render_benchmark_section([
        {
            "name": "삼쩜삼",
            "metric": "한국 핀테크 유니콘",
            "pattern": "성공 보수 18.7%·5월 종소세 환급",
        },
        {
            "name": "세모장부",
            "metric": "₩30,000+/월",
            "pattern": "프리랜서·자영업 회계·우리 = MIT 무료 + offline",
        },
    ])
    render_founder_story(
        "사서 출신 1인 PO 조기흠 (founder)·프리랜서 본인 종소세 신고 가설·"
        "삼쩜삼 (성공 보수 18.7%) 변형 = MIT 무료·offline·헌법 §14 정합."
    )
    render_disclaimer_footer(
        github_url="https://github.com/okwhrlgma-bit/freelancer-tax-helper",
        contact_email="okwhrlgma@gmail.com",
    )
    # Cycle 192: 후원·피드백 통합 (PO 마스터 프롬프트 정합·env·HTTPS 분기)
    try:
        from landing.streamlit_helper import render_donation_button, render_feedback_link

        render_donation_button(donation_url=os.environ.get("DONATION_URL", ""))
        render_feedback_link(
            feedback_url="https://github.com/okwhrlgma-bit/freelancer-tax-helper/issues",
            feedback_email="okwhrlgma@gmail.com",
        )
    except ImportError:
        pass
    # Cycle 192: UTM 추적 (st.query_params·session_state 보존)
    try:
        from analytics import label_utm_source_kr, parse_utm_source

        utm = parse_utm_source(dict(st.query_params))
        if utm:
            st.session_state.setdefault("utm_source", utm)
            st.caption(f"🧭 유입: {label_utm_source_kr(utm)}")
    except ImportError:
        pass
else:
    st.caption(
        "🔒 데이터 = 사용자 컴퓨터·🆓 MIT·📌 면책 = 자기 측정·세무사 자문 X·📜 환불 7일"
    )

st.caption(
    """
    **🔒 데이터 = 사용자 컴퓨터** (헌법 §14·offline·session_state 한정)
    **🆓 MIT 라이선스**·**📌 면책**: 자기 측정·세무사 자문 X·홈택스 신고 별도
    **📜 정합**: 소득세법 §55·국세청 단순경비율 (2026)·전자상거래법 환불 7일

    **벤치마크 변형**: 삼쩜삼 (성공 보수 18.7%) → 정액 ₩9,900/월·offline·MIT
    **데이터 차별화**: 삼쩜삼·세모장부 = 서버 / freelancer-tax-helper = 사용자 컴퓨터
    """
)
