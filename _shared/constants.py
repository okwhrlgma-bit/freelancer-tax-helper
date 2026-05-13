"""공통 상수 (Cycle 1232 신규·환율·PG 수수료·재발견 매몰비용 0).

env var 우선·default 보존·webhook_helper·payments·analytics·onboarding 통합.

PO #93 (위험 X 권한 다 허용) 정합·env 미설정 시 default 보존·실 운영 = .env 갱신.
"""

from __future__ import annotations

import os


def get_rate_usd_krw(default: int = 1_400) -> int:
    """USD→KRW 환율 (env var 우선·default 1,400).

    Args:
        default: env 미설정 시 fallback (2026-05 기준 1,400)

    Returns:
        int: 환율 (₩)·매월 수동 갱신 또는 외부 ECB·BOK API 자동 갱신 권장

    실 운영:
        export RATE_USD_KRW=1450  # 환율 변동 시
    """
    raw = os.environ.get("RATE_USD_KRW", str(default))
    try:
        rate = int(raw)
    except (ValueError, TypeError):
        return default
    if rate <= 0:
        return default
    return rate


# Module-level 캐시 (import 시점 1회 평가·env 변경 시 reload 의무)
RATE_USD_KRW: int = get_rate_usd_krw()


__all__ = [
    "RATE_USD_KRW",
    "get_rate_usd_krw",
]
