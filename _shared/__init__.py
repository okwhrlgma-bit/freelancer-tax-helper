"""30-apps 공유 패키지 (정식 승격·Cycle 104·Sandi Metz AHA·5 사용처).

ADR 0061·0064 정합·코드 우선·packages/ 승격 시점 도달.

사용처 (5·Cycle 123 한국어 폴더 정합):
- #1 kormarc-auto (kormarc-auto/·영문 유지·git history)
- #4 librarian-overtime (30-apps/04_사서_야근_추적/)
- #31 freelancer-tax-helper (30-apps/31_프리랜서_종소세_환급/)
- #32 sidehustle-tracker (30-apps/32_N잡_부업_시간_추적/)
- (예정) #2 책_KDC_분류·향후 모든 앱

9 모듈 (Cycle 155·analytics 추가):
- payments: PortOne·Stripe·LS 3 wrapper + 수수료·환불·webhook·order tampering·VAT·세금계산서·사업자번호 포맷
- legal_templates: 6 markdown (privacy·terms·refund·cookie·sla·dpa)
- auth: Better Auth·bcrypt·CSRF + LoginRateLimiter·AuditChain·email verify·사업자번호 체크섬·PII redact
- email_helper: 7 build (welcome·receipt·renewal·cancel·reset·weekly_kpi·trial_warning)
- landing: 14 Streamlit 컴포넌트 (KWCAG·legal_links·trust_badges·onboarding_bar 등)
- onboarding: 11 helper (체험·Founding·마일스톤·funnel·churn·LTV/CAC·payback·referral)
- analytics: 5 helper (KpiSnapshot·CSV export·compare·monthly·anomaly detect)·Cycle 155 신규
- AUTOMATIC_REVENUE_FLOW.md·STARTUP_ROADMAP.md·DEPLOYMENT_GUIDE.md

Apache-2.0 라이선스·Python 3.11+.
"""

from __future__ import annotations

__version__ = "0.1.0"
__license__ = "Apache-2.0"
__author__ = "조기흠 (1인 PO·founder)"

# Public API (다른 30 앱 import 정합)
__all__ = [
    "__author__",
    "__license__",
    "__version__",
]
