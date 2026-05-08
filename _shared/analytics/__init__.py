"""운영 분석 모듈 (Cycle 155 신규).

외부 발사 후 운영 데이터 분석·CSV export·주간 비교·집계.
stdlib only (pandas X·_shared 의존성 최소).

5 helper:
- KpiSnapshot: 1 시점 KPI (visits·signups·trials·paid·renewed·revenue)
- export_kpi_csv: KPI list → CSV string (Excel·Google Sheets 직접)
- compare_snapshots: 2 시점 % 변화 (성장률·alert)
- aggregate_monthly: 4주 → 1 month 집계
- detect_anomaly: 7일 평균 대비 이상치 (alert 트리거)
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class KpiSnapshot:
    """1 시점 운영 KPI 스냅샷 (주간·일간 모두 사용)."""

    timestamp: str  # ISO 8601 UTC
    visits: int = 0
    signups: int = 0
    trials: int = 0
    paid: int = 0
    renewed: int = 0
    revenue_krw: int = 0  # 결제 합계 (gross with VAT)

    def __post_init__(self) -> None:
        if not self.timestamp:
            msg = "timestamp 필수 (ISO 8601)"
            raise ValueError(msg)
        for n in (
            self.visits,
            self.signups,
            self.trials,
            self.paid,
            self.renewed,
            self.revenue_krw,
        ):
            if n < 0:
                msg = "KPI 수치 ≥ 0 의무"
                raise ValueError(msg)


def export_kpi_csv(snapshots: list[KpiSnapshot]) -> str:
    """KPI list → CSV string (Excel·Google Sheets 직접 import).

    헤더: timestamp,visits,signups,trials,paid,renewed,revenue_krw
    UTF-8 BOM 옵션 X (호출자 = 파일 저장 시 결정).
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "timestamp",
        "visits",
        "signups",
        "trials",
        "paid",
        "renewed",
        "revenue_krw",
    ])
    for s in snapshots:
        writer.writerow([
            s.timestamp,
            s.visits,
            s.signups,
            s.trials,
            s.paid,
            s.renewed,
            s.revenue_krw,
        ])
    return output.getvalue()


@dataclass(frozen=True)
class SnapshotComparison:
    """2 시점 KPI 비교 (% 변화·alert 트리거용)."""

    visits_change_pct: float
    signups_change_pct: float
    paid_change_pct: float
    revenue_change_pct: float
    label_kr: str


def _percent_change(start: int, end: int) -> float:
    """단순 % 변화 (start 0 = 0 반환)."""
    if start == 0:
        return 0.0
    return round((end - start) / start * 100, 1)


def compare_snapshots(
    older: KpiSnapshot,
    newer: KpiSnapshot,
) -> SnapshotComparison:
    """2 KPI 시점 비교·% 변화 산정."""
    visits_pct = _percent_change(older.visits, newer.visits)
    signups_pct = _percent_change(older.signups, newer.signups)
    paid_pct = _percent_change(older.paid, newer.paid)
    revenue_pct = _percent_change(older.revenue_krw, newer.revenue_krw)
    label = (
        f"방문 {visits_pct:+.1f}%·"
        f"가입 {signups_pct:+.1f}%·"
        f"결제 {paid_pct:+.1f}%·"
        f"매출 {revenue_pct:+.1f}%"
    )
    return SnapshotComparison(
        visits_change_pct=visits_pct,
        signups_change_pct=signups_pct,
        paid_change_pct=paid_pct,
        revenue_change_pct=revenue_pct,
        label_kr=label,
    )


def aggregate_monthly(weekly_snapshots: list[KpiSnapshot]) -> KpiSnapshot:
    """주간 스냅샷 list → 월간 집계 (합산·timestamp = 마지막 주)."""
    if not weekly_snapshots:
        msg = "weekly_snapshots 비어있을 수 없음"
        raise ValueError(msg)
    return KpiSnapshot(
        timestamp=weekly_snapshots[-1].timestamp,
        visits=sum(s.visits for s in weekly_snapshots),
        signups=sum(s.signups for s in weekly_snapshots),
        trials=sum(s.trials for s in weekly_snapshots),
        paid=sum(s.paid for s in weekly_snapshots),
        renewed=sum(s.renewed for s in weekly_snapshots),
        revenue_krw=sum(s.revenue_krw for s in weekly_snapshots),
    )


def detect_anomaly(
    history: list[KpiSnapshot],
    current: KpiSnapshot,
    threshold_pct: float = 50.0,
) -> str:
    """이상치 감지 (history 평균 vs current·threshold% 초과 시 alert).

    Args:
        history: 최근 N 스냅샷 (예: 7일)
        current: 현재 스냅샷
        threshold_pct: 평균 대비 변동 임계 (기본 50%)

    Returns:
        빈 string = 정상·이상 시 = 한국어 alert 메시지
    """
    if not history:
        return ""  # 비교 base 없음
    avg_visits = sum(s.visits for s in history) / len(history)
    avg_revenue = sum(s.revenue_krw for s in history) / len(history)
    alerts: list[str] = []
    if avg_visits > 0:
        change = (current.visits - avg_visits) / avg_visits * 100
        if abs(change) >= threshold_pct:
            direction = "급증" if change > 0 else "급감"
            alerts.append(f"방문 {direction} {change:+.1f}%")
    if avg_revenue > 0:
        change = (current.revenue_krw - avg_revenue) / avg_revenue * 100
        if abs(change) >= threshold_pct:
            direction = "급증" if change > 0 else "급감"
            alerts.append(f"매출 {direction} {change:+.1f}%")
    return " · ".join(alerts) if alerts else ""


__all__ = [
    "KpiSnapshot",
    "SnapshotComparison",
    "aggregate_monthly",
    "compare_snapshots",
    "detect_anomaly",
    "export_kpi_csv",
]
