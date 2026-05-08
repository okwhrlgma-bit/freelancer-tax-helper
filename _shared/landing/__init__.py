"""30-apps 공유 Streamlit 랜딩 template.

ADR 0058·0064 정합·캐시카우 통과 앱 즉시 활성·헌법 §12 KWCAG 2.2 AA 정합.
사용처: #31·#32·#1 kormarc-auto·향후 모든 앱.

벤치마크: Habit Pixel ($1K MRR/8개월·$5/월)·삼쩜삼·shipfa.st 패턴.

원칙:
- 한국어 1 페이지·KWCAG·Pretendard
- 결제 wrapper (PortOne/Stripe/LS) 자동 선택 (국가별)
- 면책 의무·전자상거래법 §17 (7일 환불)
- founder 스토리 (1인 PO·신뢰 시그널)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LandingConfig:
    """랜딩 페이지 설정."""

    app_name: str
    tagline_ko: str
    tagline_en: str = ""
    price_krw_monthly: int = 0  # 0 = 무료
    price_usd_monthly: float = 0.0
    free_trial_days: int = 14
    refund_days: int = 7  # 전자상거래법 §17
    benchmark_quote: str = ""  # "Habit Pixel $1K MRR/8개월" 등
    founder_story_ko: str = ""
    github_url: str = ""
    contact_email: str = ""


@dataclass(frozen=True)
class FAQItem:
    """FAQ 1개."""

    question_ko: str
    answer_ko: str


def default_faqs() -> list[FAQItem]:
    """5 표준 FAQ (모든 앱 공통)."""
    return [
        FAQItem(
            question_ko="결제 후 환불 가능한가요?",
            answer_ko="✅ 7일 무조건 환불 (전자상거래법 §17 정합)·1클릭 취소·월할 환불 정합 (한국 No.1 환불국).",
        ),
        FAQItem(
            question_ko="데이터는 안전한가요?",
            answer_ko="🔒 사용자 데이터 = 사용자 컴퓨터·외부 서버 X (헌법 §14)·offline 우선·PIPA 정합.",
        ),
        FAQItem(
            question_ko="LLM 답변은 100% 정확한가요?",
            answer_ko="❌ 자동 결정 X·자기 측정 보조이며 의료·법률·세무 자문 X (헌법 §11)·사용자 검수 권장.",
        ),
        FAQItem(
            question_ko="라이선스는 어떻게 되나요?",
            answer_ko="🆓 코드 = MIT/Apache·오픈 소스·향후 호스팅 SaaS 유료 (서비스 패키지·법적 책임·SLA).",
        ),
        FAQItem(
            question_ko="누가 만들었나요?",
            answer_ko="🇰🇷 한국 1인 PO 조기흠 (founder)·사서 출신·자관 6년 NPS·PO = 사용자 = 1차 검증.",
        ),
    ]


def render_pricing_section(config: LandingConfig) -> str:
    """가격 섹션 markdown."""
    if config.price_krw_monthly == 0:
        return f"## 💰 가격\n\n**무료** (MIT 라이선스)·향후 ₩{config.price_krw_monthly:,}/월"
    return (
        f"## 💰 가격\n\n"
        f"- **{config.free_trial_days}일 무료 체험**\n"
        f"- 정액 ₩{config.price_krw_monthly:,}/월\n"
        f"- {config.refund_days}일 환불 보장 (전자상거래법 §17)\n"
        f"- 1클릭 취소·자동 갱신 14일 전 알림"
    )


def render_disclaimer() -> str:
    """면책 의무 (모든 앱 공통)."""
    return (
        "\n\n---\n\n"
        "**📌 면책**: 본 서비스 = 자기 측정 보조이며 의료·법률·세무 자문 X (헌법 §11).\n"
        "**🔒 데이터**: 사용자 컴퓨터 (헌법 §14·offline·PIPA 정합).\n"
        "**🆓 라이선스**: MIT/Apache·오픈 소스.\n"
        "**📜 정합**: 전자상거래법 §17 (7일 환불)·소득세법·근로기준법.\n"
    )


__all__ = [
    "FAQItem",
    "LandingConfig",
    "default_faqs",
    "render_disclaimer",
    "render_pricing_section",
]
