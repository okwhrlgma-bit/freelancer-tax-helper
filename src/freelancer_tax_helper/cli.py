"""freelancer-tax-helper CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from freelancer_tax_helper import __version__
from freelancer_tax_helper.core import Receipt, analyze, auto_categorize_receipts


def _parse_input_file(path: Path) -> list[Receipt]:
    """JSON 영수증 list 파일 → Receipt list.

    형식 예:
    [
      {"date": "2026-03-15", "amount": 12000, "vendor": "스타벅스", "category": "meal"},
      {"date": "2026-03-20", "amount": 50000, "vendor": "교보문고"}
    ]
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("입력 파일은 영수증 list여야 합니다")
    return [
        Receipt(
            date=item["date"],
            amount=int(item["amount"]),
            vendor=item.get("vendor", ""),
            category=item.get("category", "other"),
            attachment_path=item.get("attachment_path", ""),
            memo=item.get("memo", ""),
        )
        for item in data
    ]


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="freelancer-tax-helper",
        description="한국 프리랜서 비용 처리·종소세 환급 추정 (자기 측정·헌법 §14 offline)",
    )
    parser.add_argument("--receipts", type=Path, required=True, help="JSON 영수증 파일")
    parser.add_argument("--income", type=int, required=True, help="연 수입 (원·원천공제 전)")
    parser.add_argument(
        "--business-code", default="940909", help="사업코드 (기본 940909 기타)"
    )
    parser.add_argument("--auto-classify", action="store_true", help="vendor 자동 분류")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    parser.add_argument(
        "--version", action="version", version=f"freelancer-tax-helper {__version__}"
    )

    args = parser.parse_args(argv)

    try:
        receipts = _parse_input_file(args.receipts)
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"입력 오류: {e}", file=sys.stderr)
        return 1

    if args.auto_classify:
        receipts = auto_categorize_receipts(receipts)

    report = analyze(receipts, args.income, args.business_code)

    if args.json:
        result = {
            "income": report.income,
            "deductible_total": report.deductible_total,
            "withholding_total": report.withholding_total,
            "refund_estimate": report.refund_estimate,
            "category_breakdown": report.category_breakdown,
            "simple_rate_comparison": report.simple_rate_comparison,
            "missing_warnings": report.missing_warnings,
            "recommendations": report.recommendations,
            "receipt_count": report.receipt_count,
            "business_code": report.business_code,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n💼 프리랜서 종소세 분석 (수입 ₩{report.income:,})\n")
        print(f"  영수증: {report.receipt_count}건")
        print(f"  사업코드: {report.business_code}")
        print(f"  원천공제 (3.3%): ₩{report.withholding_total:,}\n")

        print("  📂 카테고리별 인정 비용:")
        for cat, amount in report.category_breakdown.items():
            if amount > 0:
                print(f"    {cat:14s} ₩{amount:>12,}")
        print(f"    {'─' * 30}")
        print(f"    {'합계':14s} ₩{report.deductible_total:>12,}\n")

        cmp = report.simple_rate_comparison
        print("  📊 비용 비교:")
        print(f"    직접 비용:      ₩{cmp['direct_cost']:>12,}")
        print(f"    단순경비율:     ₩{cmp['simple_rate_cost']:>12,}")
        print(f"    적용 (큰 값):   ₩{cmp['deductible_used']:>12,}\n")

        print("  💰 예상 세액:")
        print(f"    소득세:         ₩{cmp['estimated_tax']:>12,}")
        print(f"    지방소득세:     ₩{cmp['local_tax']:>12,}")
        print(f"    합계:           ₩{cmp['total_tax']:>12,}")
        sign = "환급" if report.refund_estimate >= 0 else "추가 납부"
        print(f"    {sign}:         ₩{abs(report.refund_estimate):>12,}\n")

        if report.missing_warnings:
            print("  🚨 경고:")
            for w in report.missing_warnings:
                print(f"    {w}")
            print()

        print("  📝 권고:")
        for r in report.recommendations:
            print(f"    {r}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
