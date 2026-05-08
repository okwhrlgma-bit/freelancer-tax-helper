"""analytics 모듈 tests (Cycle 155)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analytics import (
    KpiSnapshot,
    aggregate_monthly,
    compare_snapshots,
    detect_anomaly,
    export_kpi_csv,
)


class TestKpiSnapshot:
    def test_basic_construction(self):
        s = KpiSnapshot(
            timestamp="2026-05-09T00:00:00+00:00",
            visits=1_000,
            signups=100,
            trials=80,
            paid=5,
            renewed=4,
            revenue_krw=49_500,
        )
        assert s.visits == 1_000
        assert s.revenue_krw == 49_500

    def test_negative_rejected(self):
        with pytest.raises(ValueError, match="≥ 0"):
            KpiSnapshot(
                timestamp="2026-05-09T00:00:00+00:00",
                visits=-1,
            )

    def test_empty_timestamp_rejected(self):
        with pytest.raises(ValueError, match="timestamp"):
            KpiSnapshot(timestamp="")

    def test_defaults_zero(self):
        s = KpiSnapshot(timestamp="2026-05-09T00:00:00+00:00")
        assert s.visits == 0
        assert s.revenue_krw == 0


class TestExportCsv:
    def test_csv_header_present(self):
        s = KpiSnapshot(
            timestamp="2026-05-09T00:00:00+00:00",
            visits=1_000,
            paid=5,
            revenue_krw=49_500,
        )
        csv_str = export_kpi_csv([s])
        first_line = csv_str.splitlines()[0]
        assert "timestamp" in first_line
        assert "visits" in first_line
        assert "revenue_krw" in first_line

    def test_csv_row_data(self):
        s = KpiSnapshot(
            timestamp="2026-05-09T00:00:00+00:00",
            visits=1_000,
            signups=100,
            paid=5,
            revenue_krw=49_500,
        )
        csv_str = export_kpi_csv([s])
        assert "1000" in csv_str
        assert "49500" in csv_str

    def test_empty_list_only_header(self):
        csv_str = export_kpi_csv([])
        lines = csv_str.strip().splitlines()
        assert len(lines) == 1  # header only

    def test_multiple_snapshots(self):
        s1 = KpiSnapshot(timestamp="2026-W18", visits=500, paid=2)
        s2 = KpiSnapshot(timestamp="2026-W19", visits=1_000, paid=5)
        csv_str = export_kpi_csv([s1, s2])
        lines = csv_str.strip().splitlines()
        assert len(lines) == 3  # header + 2 rows


class TestCompareSnapshots:
    def test_growth_100_percent(self):
        s1 = KpiSnapshot(timestamp="W18", visits=500, paid=2, revenue_krw=19_800)
        s2 = KpiSnapshot(timestamp="W19", visits=1_000, paid=4, revenue_krw=39_600)
        cmp = compare_snapshots(s1, s2)
        assert cmp.visits_change_pct == 100.0
        assert cmp.paid_change_pct == 100.0
        assert cmp.revenue_change_pct == 100.0
        assert "+100.0%" in cmp.label_kr

    def test_decline_50_percent(self):
        s1 = KpiSnapshot(timestamp="W18", visits=1_000, paid=10)
        s2 = KpiSnapshot(timestamp="W19", visits=500, paid=5)
        cmp = compare_snapshots(s1, s2)
        assert cmp.visits_change_pct == -50.0
        assert "-50.0%" in cmp.label_kr

    def test_zero_base_safe(self):
        s1 = KpiSnapshot(timestamp="W18", visits=0)
        s2 = KpiSnapshot(timestamp="W19", visits=100)
        cmp = compare_snapshots(s1, s2)
        # 0 base = 0 반환 (무한대 회피)
        assert cmp.visits_change_pct == 0.0


class TestAggregateMonthly:
    def test_4_weeks_summed(self):
        weeks = [
            KpiSnapshot(timestamp=f"W{i}", visits=1_000, paid=5, revenue_krw=49_500)
            for i in range(18, 22)
        ]
        monthly = aggregate_monthly(weeks)
        assert monthly.visits == 4_000
        assert monthly.paid == 20
        assert monthly.revenue_krw == 198_000
        assert monthly.timestamp == "W21"  # 마지막 주

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="비어있"):
            aggregate_monthly([])

    def test_single_week(self):
        s = KpiSnapshot(timestamp="W19", visits=500, paid=2)
        monthly = aggregate_monthly([s])
        assert monthly.visits == 500
        assert monthly.paid == 2


class TestDetectAnomaly:
    def test_normal_no_alert(self):
        history = [
            KpiSnapshot(timestamp=f"D{i}", visits=1_000, revenue_krw=50_000)
            for i in range(7)
        ]
        current = KpiSnapshot(timestamp="D8", visits=1_100, revenue_krw=52_000)
        assert detect_anomaly(history, current) == ""

    def test_visit_surge_alerts(self):
        history = [
            KpiSnapshot(timestamp=f"D{i}", visits=1_000, revenue_krw=50_000)
            for i in range(7)
        ]
        # 70% 증가 = threshold 50% 초과
        current = KpiSnapshot(timestamp="D8", visits=1_700, revenue_krw=50_000)
        alert = detect_anomaly(history, current)
        assert "방문 급증" in alert
        assert "+70" in alert

    def test_revenue_drop_alerts(self):
        history = [
            KpiSnapshot(timestamp=f"D{i}", visits=1_000, revenue_krw=50_000)
            for i in range(7)
        ]
        current = KpiSnapshot(timestamp="D8", visits=1_000, revenue_krw=10_000)
        alert = detect_anomaly(history, current)
        assert "매출 급감" in alert

    def test_empty_history_no_alert(self):
        current = KpiSnapshot(timestamp="D8", visits=1_000)
        assert detect_anomaly([], current) == ""

    def test_custom_threshold(self):
        history = [KpiSnapshot(timestamp=f"D{i}", visits=1_000) for i in range(7)]
        # 20% 증가·threshold 30% = 정상
        current = KpiSnapshot(timestamp="D8", visits=1_200)
        assert detect_anomaly(history, current, threshold_pct=30.0) == ""
