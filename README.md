# freelancer-tax-helper

> **한국 프리랜서 비용 처리·종소세 환급 추정·누락 경고**
> 30 apps #31·페인 P-2026-004 (90/100 GO)·ADR 0055 게이트 통과·MIT
> **외부 발사 검증 단계** (사업자 등록 보류·해외 PG 검증 후 결제 활성)

[![Streamlit Cloud](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://freelancer-tax-helper.streamlit.app)
[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

## 정합 정책

- 헌법 §14: 사용자 데이터 = 사용자 컴퓨터·외부 서버 X (offline·session_state)
- 헌법 §10: AI 사실 = 검수 단계 보존·100% 자동 X
- 헌법 §11: 신뢰도 = 카테고리 (raw % X)
- 전자상거래법 §17: 환불 7일
- 면책: 자기 측정 보조·세무사 자문 X·홈택스 신고 별도

## 1줄 설명

```
input  = list[Receipt(date, amount, vendor, category?)] + 연 수입 + 사업코드
output = TaxReport(deductible_total, breakdown, refund_estimate, warnings, recommendations)
```

## 빠른 사용

```bash
pip install -e .
echo '[
  {"date":"2026-01-15","amount":35000,"vendor":"스타벅스","category":"meal"},
  {"date":"2026-02-03","amount":80000,"vendor":"교보문고","category":"books"}
]' > receipts.json
freelancer-tax-helper --receipts receipts.json --income 30000000 --business-code 940100
```

출력:
```
💼 프리랜서 종소세 분석 (수입 ₩30,000,000)
  영수증: 2건·사업코드: 940100·원천공제 (3.3%): ₩990,000

  📂 카테고리별 인정 비용:
    meal           ₩      35,000
    books          ₩      80,000
    합계             ₩     115,000

  📊 비용 비교:
    직접 비용:    ₩115,000
    단순경비율:   ₩20,280,000  (수입 × 67.6% IT)
    적용 (큰 값): ₩20,280,000

  💰 예상 세액:
    합계:    ₩542,520
    환급:    ₩447,480

  📝 권고: 단순경비율 적용 유리·영수증 30건 미만 매월 정리 권고
```

## 누구를 위한 도구

- **한국 프리랜서** (사업소득자·3.3% 원천공제): IT 개발자·디자이너·작가·강사·번역가·컨설턴트·사진작가
- **5월 종소세 신고 대비**: 환급 추정·누락 영수증 사전 점검
- **단순경비율 vs 직접 비용 자동 비교**: 둘 중 환급 ↑ 추천

## 핵심 차별화 (vs 삼쩜삼·세모장부)

| 항목 | 삼쩜삼 | 세모장부 | freelancer-tax-helper |
|---|---|---|---|
| 가격 | 환급액 18.7% (성공 보수) | ₩30,000+/월 | **MIT 무료 / 향후 ₩4,900~9,900/월** |
| 데이터 위치 | 삼쩜삼 서버 | 세모장부 서버 | **사용자 컴퓨터 (헌법 §14)** |
| offline | X | X | ✅ |
| 라이선스 | 비공개 | 비공개 | **MIT (오픈)** |
| LLM 옵션 | X | X | BYOK (다음 cycle) |

## 사업코드별 단순경비율 (2026 기준 추정)

| 코드 | 분야 | 비율 |
|---|---|---|
| 940100 | IT 개발자·소프트웨어 | 67.6% |
| 940200 | 디자인·일러스트 | 64.2% |
| 940300 | 작가·번역 | 58.7% |
| 940500 | 컨설팅 | 65.8% |
| 940600 | 사진·영상 | 61.2% |
| 940904 | 작가 | 58.7% |
| 940906 | 강사·번역 | 64.1% |
| 940909 | 기타 자영업 (기본) | 64.1% |

## 비용 카테고리 10 분류

식대 (meal)·교통 (transport)·통신 (comm)·도서 (books)·교육 (education)·소모품 (supplies)·임차 (rent)·외주 (outsourcing)·접대 (entertainment·50% 인정)·기타 (other).

vendor 자동 분류 = 키워드 매칭 (스타벅스→식대, 교보문고→도서, 위워크→임차 등). `--auto-classify` 옵션.

## 핵심 원칙 (헌법·ADR 정합)

- 🔒 **자관 데이터 X**: 영수증 = 사용자 컴퓨터·SaaS 서버 X (헌법 §14)
- 📚 **권위 보존**: 자동 결정 X·"세무사 자문 X" 면책 (헌법 §11)
- 🌐 **offline 우선**: 외부 API X·룰 기반
- 🇰🇷 **한국어 friendly**: 국세청 용어·근로기준법 인용
- 🆓 **MIT**

## Python API

```python
from freelancer_tax_helper import Receipt, analyze, auto_categorize_receipts

receipts = [
    Receipt(date="2026-01-15", amount=35_000, vendor="스타벅스", category="meal"),
    Receipt(date="2026-03-10", amount=250_000, vendor="위워크"),  # category 미입력
]
receipts = auto_categorize_receipts(receipts)  # vendor → 자동 분류

report = analyze(receipts, income=30_000_000, business_code="940100")
print(f"환급 추정: ₩{report.refund_estimate:,}")
```

## 평가축 통과 (ADR 0053)

- ✅ 단일 기능 명확 (1줄)
- ✅ tests 33 (≥15 초과)
- ✅ ruff 0 errors
- ✅ 1 cycle 완성
- ✅ MIT
- ✅ 한국어 docs/CLI
- ✅ 자관 데이터 X
- ✅ offline (외부 API X)

## ADR 0055 게이트 통과 점수

| 항목 | 점수 |
|---|---|
| 페인 (P-2026-004) | direct quote + 결제 의향 강함 |
| 시장성 | 90/100 |
| 캐시카우 | 100/100 |
| Q5 컴플 | PASS |
| 자동 결정 | **GO** ✅ |

## 한계

- 영수증 OCR 미구현 (BYOK 옵션·다음 cycle)
- 매월 자동 import (구글 드라이브) 미구현
- Streamlit UI 미구현
- 누진세율 단순화 (정밀 신고 = 홈택스 또는 세무사)

## 다음 cycle 계획

- 영수증 OCR (BYOK Claude Sonnet 4.6 Vision)
- 종소세 신고서 PDF 자동 생성 (홈택스 양식)
- Streamlit UI (1인 사업자 친화)
- 동료 비교 (anonymous·옵트인)

## 면책

- 본 도구 = 자기 측정 보조
- 세무사 자문 X·국세청 공식 신고 X
- 환급 추정 = 단순화·실제 신고 = 홈택스 또는 세무사 위임
- 단순경비율은 매년 국세청 고시 기준에 따라 변경 가능

## 출처

- 국세청 「2026년 사업소득 단순경비율」
- 소득세법 §55 (누진세율)·시행령
- clobe.ai 「2026년 달라진 프리랜서 비용처리 기준」 (페인 출처)
- ADR 0052·0053·0054·0055 (kormarc-auto)
