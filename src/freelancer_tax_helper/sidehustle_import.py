"""sidehustle-tracker → freelancer-tax-helper 역방향 import (Cycle 106).

ADR 0061·Cycle 94 양방향 통합 완성·코드 우선.
부업 매출 JSON (sidehustle 형식) → Receipt list 자동 변환·종소세 신고 가능.

원칙:
- sidehustle-tracker 의존 X (JSON 형식만)·독립 import 가능
- 사용자 검수 의무 (자동 등록 X·검수 후 income 입력)
- 헌법 §14 정합 (사용자 컴퓨터 JSON·서버 X)
"""

from __future__ import annotations

import json
from pathlib import Path

from freelancer_tax_helper.core import Receipt


def parse_sidehustle_blocks(json_data: list[dict]) -> list[Receipt]:
    """sidehustle TimeBlock JSON → Receipt list (side type + revenue 만).

    sidehustle 형식 가정:
    [
      {"date": "2026-05-04", "start": "20:00", "end": "23:00",
       "project": "블로그", "type": "side", "revenue_krw": 150000},
      ...
    ]

    Returns:
        Receipt list (category="other"·사용자 검수 권장)
    """
    receipts: list[Receipt] = []
    for item in json_data:
        if item.get("type") != "side":
            continue
        revenue = int(item.get("revenue_krw", 0))
        if revenue <= 0:
            continue
        receipts.append(
            Receipt(
                date=str(item.get("date", "")),
                amount=revenue,
                vendor=str(item.get("project", "(미입력)")),
                category="other",  # 사용자 검수 의무
                memo=f"sidehustle import·{item.get('start', '')}~{item.get('end', '')}",
            )
        )
    return receipts


def parse_sidehustle_export_file(path: Path | str) -> list[Receipt]:
    """sidehustle JSON 파일 → Receipt list (CLI export 호환)."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"파일 없음: {file_path}")

    raw = json.loads(file_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        # CLI --json output 형식 (analyze 결과)·daily_split 추출 X·blocks 직접 X
        # → 사용자 검수 의무·간단 형식만 지원
        raise ValueError(
            "sidehustle blocks list 필요 (analyze 결과 X)·"
            "사용 패턴: TimeBlock list JSON 직접 export"
        )
    if not isinstance(raw, list):
        raise ValueError("sidehustle export = list 형식이어야 합니다")

    return parse_sidehustle_blocks(raw)


def estimate_combined_income(receipts: list[Receipt]) -> int:
    """Receipt 매출 합계 → 추정 income (sidehustle 부업 매출만)."""
    return sum(r.amount for r in receipts)


__all__ = [
    "estimate_combined_income",
    "parse_sidehustle_blocks",
    "parse_sidehustle_export_file",
]
