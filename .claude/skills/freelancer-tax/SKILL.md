---
name: freelancer-tax-helper
description: 한국 프리랜서 영수증 + 수입 → 종소세 환급 추정·단순경비율 vs 직접 비용 자동 비교·offline MIT
license: MIT
version: 0.1.0
language: ko
tags: [korean, freelancer, tax, income, refund]
---

# freelancer-tax-helper Skill

> 한국 사업소득자 (3.3% 원천공제) 5월 종소세 환급 사전 추정·삼쩜삼 변형 (정액 무료·MIT).

## Inputs

- `receipts` (list[Receipt]·필수):
  - `date` (string·YYYY-MM-DD)
  - `amount` (int·원)
  - `vendor` (string)
  - `category` (enum·옵션·자동 분류)
- `income` (int·필수): 연 수입 (원천공제 전 총액)
- `business_code` (string·옵션·기본 "940909"):
  - 940100 IT (67.6%)·940200 디자인 (64.2%)·940300 작가 (58.7%)
  - 940500 컨설팅·940600 사진·940904 작가·940906 강사·940909 기타

## Outputs

- `deductible_total` (int): 인정 비용 합계
- `refund_estimate` (int): 환급 예상 (양수) or 추가 납부 (음수)
- `simple_rate_comparison` (dict):
  - `direct_cost`·`simple_rate_cost`·`deductible_used` (둘 중 큰 값)
- `category_breakdown` (dict): 10 카테고리별 인정 비용
- `missing_warnings` (list): 누락 영수증 경고
- `recommendations` (list): 사용자 친화 권고 (한국어)

## Constitution

- §3 HARD RULES (timeout·UTF-8)
- §11 카테고리만 (raw % X)
- §14 영수증 = 사용자 컴퓨터 (외부 서버 X)

## Algorithm

- 단순경비율 8 사업코드 매트릭스 (국세청 2026)
- 누진세율 8 구간 (소득세법 §55·6~45%)
- 사업소득 원천공제 3.3% (소득세 3% + 지방세 0.3%)
- 접대비 50% 인정 한도

## Benchmark

- 삼쩜삼 (한국 핀테크 유니콘): 환급 18.7% 성공 보수
- 세모장부: ₩30,000+/월
- 우리 = MIT 무료 → 향후 ₩4,900~9,900/월 (정액)
- 차별화: 데이터 사용자 컴퓨터·offline·BYOK 옵션

## 사용 예시

```python
from freelancer_tax_helper import Receipt, analyze

receipts = [
    Receipt(date="2026-01-15", amount=35_000, vendor="스타벅스", category="meal"),
    Receipt(date="2026-02-03", amount=80_000, vendor="교보문고", category="books"),
]
report = analyze(receipts, income=30_000_000, business_code="940100")
print(f"환급 추정: ₩{report.refund_estimate:,}")
# 환급 추정: ₩447,480
```

## 면책

- 자기 측정 보조·세무사 자문 X·홈택스 신고 별도

## 정합

- ADR 0053·0055·0058 (배포 가능 4 조건 통과)·페인 P-2026-004 GO (90/100)
- 30 apps #31·33 tests + ruff 0
- I-003 Skills Marketplace 변환 후보 (한국 프리랜서 niche)
