"""sidehustle_import 회귀 (Cycle 106·역방향 통합)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from freelancer_tax_helper.core import Receipt
from freelancer_tax_helper.sidehustle_import import (
    estimate_combined_income,
    parse_sidehustle_blocks,
    parse_sidehustle_export_file,
)


class TestParseSidehustleBlocks:
    def test_side_type_with_revenue_converted(self) -> None:
        blocks = [
            {
                "date": "2026-05-04",
                "start": "20:00",
                "end": "23:00",
                "project": "블로그",
                "type": "side",
                "revenue_krw": 150_000,
            },
        ]
        receipts = parse_sidehustle_blocks(blocks)
        assert len(receipts) == 1
        assert receipts[0].amount == 150_000
        assert receipts[0].vendor == "블로그"
        assert receipts[0].category == "other"
        assert "sidehustle import" in receipts[0].memo

    def test_main_type_skipped(self) -> None:
        blocks = [
            {"date": "2026-05-04", "start": "09:00", "end": "18:00",
             "project": "회사", "type": "main"},
        ]
        receipts = parse_sidehustle_blocks(blocks)
        assert len(receipts) == 0

    def test_zero_revenue_skipped(self) -> None:
        blocks = [
            {"date": "2026-05-04", "start": "20:00", "end": "22:00",
             "project": "블로그", "type": "side", "revenue_krw": 0},
        ]
        receipts = parse_sidehustle_blocks(blocks)
        assert len(receipts) == 0

    def test_multiple_side_blocks(self) -> None:
        blocks = [
            {"date": "2026-05-04", "start": "20:00", "end": "23:00",
             "project": "블로그", "type": "side", "revenue_krw": 150_000},
            {"date": "2026-05-05", "start": "21:00", "end": "23:00",
             "project": "유튜브", "type": "side", "revenue_krw": 80_000},
        ]
        receipts = parse_sidehustle_blocks(blocks)
        assert len(receipts) == 2
        assert receipts[1].amount == 80_000

    def test_empty_input(self) -> None:
        assert parse_sidehustle_blocks([]) == []


class TestParseFile:
    def test_valid_file(self, tmp_path: Path) -> None:
        data = [
            {"date": "2026-05-04", "start": "20:00", "end": "23:00",
             "project": "x", "type": "side", "revenue_krw": 100_000},
        ]
        p = tmp_path / "blocks.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        receipts = parse_sidehustle_export_file(p)
        assert len(receipts) == 1
        assert receipts[0].amount == 100_000

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            parse_sidehustle_export_file(tmp_path / "missing.json")

    def test_dict_format_rejected(self, tmp_path: Path) -> None:
        # analyze --json 결과 (dict) = 거부·blocks list만 허용
        p = tmp_path / "report.json"
        p.write_text(json.dumps({"weekly_main_hours": 40}), encoding="utf-8")
        with pytest.raises(ValueError, match="blocks list"):
            parse_sidehustle_export_file(p)


class TestCombinedIncome:
    def test_sum_correct(self) -> None:
        receipts = [
            Receipt(date="2026-05-04", amount=150_000, vendor="블로그", category="other"),
            Receipt(date="2026-05-05", amount=80_000, vendor="유튜브", category="other"),
        ]
        assert estimate_combined_income(receipts) == 230_000

    def test_empty_zero(self) -> None:
        assert estimate_combined_income([]) == 0
