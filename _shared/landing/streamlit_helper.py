"""Streamlit 공용 컴포넌트 (30 apps 재사용·KWCAG 2.2 AA·Pretendard).

ADR 0058·0064 정합·캐시카우 통과 앱 = 즉시 활성.
사용처: #31·#32·#1 kormarc-auto·향후 모든 앱.
"""

from __future__ import annotations

# Streamlit import = 옵션 (랜딩만 사용·core X)
try:
    import streamlit as st  # type: ignore[import-not-found]

    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False
    st = None  # type: ignore[assignment]


def render_korean_header(app_name: str, tagline: str) -> None:
    """한국어 hero 섹션 (Pretendard·KRDS Korea blue 60)."""
    if not STREAMLIT_AVAILABLE or st is None:
        return
    st.markdown(
        f"""
        # {app_name}

        **{tagline}**
        """
    )


def render_pricing_card(
    plan_name: str,
    price_krw: int,
    features: list[str],
    cta_label: str = "시작하기",
    is_recommended: bool = False,
) -> bool:
    """가격 카드 + CTA 버튼·반환 True = 클릭."""
    if not STREAMLIT_AVAILABLE or st is None:
        return False

    container = st.container(border=True)
    with container:
        if is_recommended:
            st.markdown("⭐ **추천 플랜**")
        st.markdown(f"### {plan_name}")
        if price_krw == 0:
            st.markdown("**무료** (MIT 라이선스)")
        else:
            st.markdown(f"**₩{price_krw:,}/월**")

        for feat in features:
            st.markdown(f"- {feat}")

        return st.button(cta_label, type="primary" if is_recommended else "secondary")


def render_disclaimer_footer(github_url: str = "", contact_email: str = "") -> None:
    """면책 + 정합 footer (모든 앱 공통)."""
    if not STREAMLIT_AVAILABLE or st is None:
        return

    parts = [
        "**🔒 데이터** = 사용자 컴퓨터 (헌법 §14·offline·PIPA 정합)",
        "**🆓 라이선스** = MIT/Apache·오픈 소스",
        "**📌 면책** = 자기 측정 보조·의료/법률/세무 자문 X (헌법 §11)",
        "**📜 환불** = 7일 무조건 (전자상거래법 §17)",
    ]
    if github_url:
        parts.append(f"**📂 GitHub**: {github_url}")
    if contact_email:
        parts.append(f"**📧 문의**: {contact_email}")

    st.divider()
    st.caption("\n\n".join(parts))


def render_founder_story(story_ko: str) -> None:
    """founder 신뢰 시그널 (1인 PO·한국)."""
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not story_ko:
        return
    with st.expander("👤 founder 스토리 (1인 PO·한국)"):
        st.markdown(story_ko)


def render_faq_section(faqs: list[dict[str, str]]) -> None:
    """FAQ 섹션·각 FAQ = expander."""
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not faqs:
        return
    st.subheader("❓ FAQ")
    for faq in faqs:
        with st.expander(faq.get("question_ko", "")):
            st.markdown(faq.get("answer_ko", ""))


def render_metric_grid(metrics: dict[str, str], cols: int = 3) -> None:
    """메트릭 그리드 (3 컬럼 기본·KWCAG 정합)·Cycle 109."""
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not metrics:
        return
    columns = st.columns(cols)
    for i, (label, value) in enumerate(metrics.items()):
        columns[i % cols].metric(label, value)


def render_persona_match(personas: list[dict[str, str]]) -> None:
    """대상 페르소나 카드·정직 시그널 (founder fit·매출 가능성)·Cycle 109."""
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not personas:
        return
    st.subheader("👥 누구를 위한 도구?")
    for p in personas:
        with st.expander(p.get("title_ko", "")):
            st.markdown(p.get("description_ko", ""))
            if "fit_score" in p:
                st.caption(f"**fit**: {p['fit_score']}")


def render_benchmark_section(benchmarks: list[dict[str, str]]) -> None:
    """벤치마크 사례 (인디 검증·ADR 0065 정합)·Cycle 109."""
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not benchmarks:
        return
    st.subheader("📊 벤치마크 (인디 검증)")
    for b in benchmarks:
        col1, col2, col3 = st.columns(3)
        col1.markdown(f"**{b.get('name', '')}**")
        col2.markdown(b.get("metric", ""))
        col3.markdown(b.get("pattern", ""))


def render_pricing_grid(plans: list[dict[str, object]]) -> str | None:
    """가격 플랜 그리드 (여러 카드·반환 = 클릭 plan name)·Cycle 119."""
    if not STREAMLIT_AVAILABLE or st is None:
        return None
    if not plans:
        return None

    st.subheader("💰 가격")
    columns = st.columns(len(plans))
    selected: str | None = None
    for i, plan in enumerate(plans):
        with columns[i]:
            container = st.container(border=True)
            with container:
                if plan.get("recommended", False):
                    st.markdown("⭐ **추천**")
                st.markdown(f"### {plan.get('name', '')}")
                price_krw = plan.get("price_krw", 0)
                if price_krw == 0:
                    st.markdown("**무료**")
                else:
                    st.markdown(f"**₩{int(price_krw):,}/월**")
                features = plan.get("features", [])
                if isinstance(features, list):
                    for f in features:
                        st.markdown(f"- {f}")
                if st.button(
                    plan.get("cta", "선택"),
                    key=f"pricing_{i}",
                    type="primary" if plan.get("recommended", False) else "secondary",
                ):
                    selected = str(plan.get("name", ""))
    return selected


def render_cta_bar(label: str, sublabel: str = "") -> bool:
    """CTA 강조 영역 (큰 버튼·sticky 시각)·Cycle 119."""
    if not STREAMLIT_AVAILABLE or st is None:
        return False
    if sublabel:
        st.caption(sublabel)
    return st.button(label, type="primary", use_container_width=True)


def render_features_comparison(rows: list[dict[str, str]]) -> None:
    """기능 비교 표 (vs 경쟁사·차별화 시그널)·Cycle 119."""
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not rows:
        return
    st.subheader("📊 vs 경쟁사")
    st.dataframe(rows, hide_index=True)


def render_legal_links(
    base_url: str = "",
    include: tuple[str, ...] = (
        "privacy",
        "terms",
        "refund",
        "cookie",
        "sla",
        "dpa",
    ),
) -> None:
    """legal markdown 6 footer 통합 링크 (외부 발사 시 의무)·Cycle 154.

    Args:
        base_url: 호스팅 base URL (예: "https://app.example.com/legal")
                  빈 문자열 = 상대 경로 (`/legal/<name>`)
        include: 표시할 markdown 키 (기본 6 모두)

    표시 라벨 (한국어 정합·PIPA·전자상거래법):
        privacy → "처리방침" (PIPA 의무 표시)
        terms   → "이용약관" (전자상거래법 §10 의무)
        refund  → "환불정책" (전자상거래법 §17 의무)
        cookie  → "쿠키정책" (정보통신망법 §50의5)
        sla     → "서비스 약정"
        dpa     → "위탁계약"
    """
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not include:
        return
    labels: dict[str, str] = {
        "privacy": "처리방침",
        "terms": "이용약관",
        "refund": "환불정책",
        "cookie": "쿠키정책",
        "sla": "서비스 약정",
        "dpa": "위탁계약",
    }
    parts: list[str] = []
    for key in include:
        if key not in labels:
            continue
        href = f"{base_url}/{key}" if base_url else f"/legal/{key}"
        parts.append(f"[{labels[key]}]({href})")
    if parts:
        st.caption(" · ".join(parts))


def render_trust_badges(badges: list[dict[str, str]]) -> None:
    """신뢰 배지 렌더링 (PIPA·법무·offline·KOR 등 시각·landing footer)·Cycle 148.

    Args:
        badges: list of {"icon": str, "label": str, "tooltip": str (optional)}

    예:
        [{"icon": "🔒", "label": "PIPA 5/5"},
         {"icon": "🆓", "label": "MIT"},
         {"icon": "📜", "label": "전자상거래법"}]
    """
    if not STREAMLIT_AVAILABLE or st is None:
        return
    if not badges:
        return
    cols = st.columns(min(len(badges), 5))
    for i, badge in enumerate(badges[:5]):
        with cols[i]:
            tooltip = badge.get("tooltip", badge.get("label", ""))
            st.markdown(
                f"<div style='text-align:center;padding:8px;'>"
                f"<div style='font-size:28px'>{badge.get('icon', '✅')}</div>"
                f"<div style='font-size:12px;color:#555' title='{tooltip}'>"
                f"{badge.get('label', '')}</div></div>",
                unsafe_allow_html=True,
            )


def render_onboarding_bar(
    founding_label: str,
    milestone_label: str,
    trial_label: str = "",
) -> None:
    """온보딩 바 (Founding 슬롯 + 매출 마일스톤 + 선택적 체험 카운터)·Cycle 133.

    onboarding 모듈과 통합·#4·#31·#32 공통 사용·DRY (Sandi Metz AHA).

    Args:
        founding_label: calculate_founding_slot(...).label_kr 결과
        milestone_label: get_current_milestone(...).label_kr 결과
        trial_label: calculate_trial_status(...).label_kr (선택·체험 시작 후 표시)
    """
    if not STREAMLIT_AVAILABLE or st is None:
        return
    cols_count = 3 if trial_label else 2
    cols = st.columns(cols_count)
    cols[0].info(f"🎯 {founding_label}")
    cols[1].info(f"📈 {milestone_label}")
    if trial_label:
        cols[2].info(f"⏰ {trial_label}")


__all__ = [
    "STREAMLIT_AVAILABLE",
    "render_benchmark_section",
    "render_cta_bar",
    "render_disclaimer_footer",
    "render_faq_section",
    "render_features_comparison",
    "render_founder_story",
    "render_korean_header",
    "render_metric_grid",
    "render_legal_links",
    "render_onboarding_bar",
    "render_persona_match",
    "render_pricing_card",
    "render_pricing_grid",
    "render_trust_badges",
]
