# spec.md — freelancer-tax-helper (#31 / 30 apps + 1)

> ADR 0053·0055 정합·페인 P-2026-004 GO (90/100)·1주 1앱 사이클·MIT
> 1줄 설명: **영수증 list → 종소세 비용 처리·환급 추정·누락 경고 (한국 프리랜서)**

## 0. 단일 기능 (1줄)

```
input  = list[Receipt(date, amount, vendor, category?, attachment_path?, memo?)]
output = TaxReport(deductible_total, category_breakdown, missing_warnings,
                   refund_estimate, simple_rate_comparison, recommendations)
```

## 1. 페인 검증 (ADR 0055 통과)

- 페인 ID: P-2026-004
- 출처: clobe.ai 「2026년 달라진 프리랜서 비용처리 기준」
- 시장 점수: 90/100
- 캐시카우 점수: 100/100
- Q5 PASS (PIPA·헌법 §14 정합·사용자 컴퓨터)
- 자동 결정: GO ✅

## 2. 평가축 (ADR 0053)

| 항목 | 값 |
|---|---|
| 단일 기능 명확성 | ✅ 1줄 |
| 버그 0 | ✅ tests ≥ 15 + ruff 0 |
| 1주 완성 | ✅ 1 cycle = spec + 코드 + tests |
| 라이선스 | ✅ MIT |
| 한국어 friendly | ✅ docs·UI 한국어·국세청 용어 |
| 자관 데이터 X | ✅ 영수증 = 사용자 컴퓨터·SaaS 서버 X |

## 3. 한국 종소세 (사업소득자) 핵심 룰

### 단순경비율 (수입 ≤ 7,500만원)
- 사업자등록번호별 코드 자동 적용
- 프리랜서 주요 코드:
  - 940909 기타 자영업: 64.1%
  - 940904 작가: 58.7%
  - 940906 강사·번역: 64.1%
  - 940100 IT 개발자: 67.6%
- 비용 = 수입 × 경비율 (영수증 X·자동)

### 기준경비율 (수입 > 7,500만원)
- 주요 비용 (인건비·임차·매입) = 영수증 필수
- 기타 비용 = 기준경비율 (예: 22.4%)

### 본 앱 = 단순 + 직접 비용 비교
1. 영수증 비용 합계 (직접 입력 모드)
2. 단순경비율 자동 계산 (수입 + 사업코드)
3. **둘 중 큰 값 = 환급 ↑** 자동 판단

## 4. 비용 카테고리 (10 분류)

| 카테고리 | 인정 가능 | 영수증 필수 |
|---|---|---|
| meal | 식대 (업무 미팅) | ✅ |
| transport | 교통 (대중·택시·주유) | ✅ |
| comm | 통신 (휴대폰·인터넷·서버) | ✅ |
| books | 도서·자료 (직무 관련) | ✅ |
| education | 교육 (학원·온라인 코스·세미나) | ✅ |
| supplies | 사무 소모품 (문구·잉크) | ✅ |
| rent | 임차 (사무실·코워킹) | ✅ |
| outsourcing | 외주비 (디자이너·번역) | ✅ + 원천세 |
| entertainment | 접대 (인정 한도 50%) | ✅ |
| other | 기타 | ✅ |

## 5. 환급 추정 알고리즘

```python
withholding = income * 0.033  # 3.3% 사업소득세 원천공제
direct_cost = sum(receipts)
simple_rate_cost = income * simple_rate(business_code)

# 두 가지 중 환급 ↑ 선택
deductible = max(direct_cost, simple_rate_cost)

taxable = income - deductible - personal_deduction(150만 기본공제)
estimated_tax = progressive_rate(taxable)  # 6%·15%·24%·35%·38%·40%·42%·45%

refund = withholding - estimated_tax
```

## 6. 누락 경고

- 매월 영수증 0건 → "이번 달 비용 영수증이 없습니다·놓친 항목 점검"
- 통신·임차 = 매월 자동 발생인데 0건 → "통신비 영수증 누락 확인"
- 카테고리별 합계 0 → 알림

## 7. 출력 형식

```python
@dataclass(frozen=True)
class Receipt:
    date: str           # ISO 8601
    amount: int         # 원
    vendor: str
    category: str = "other"
    attachment_path: str = ""
    memo: str = ""

@dataclass(frozen=True)
class TaxReport:
    deductible_total: int
    category_breakdown: dict[str, int]
    missing_warnings: list[str]
    refund_estimate: int           # 양수 = 환급·음수 = 추가 납부
    simple_rate_comparison: dict[str, int]
    recommendations: list[str]
    income: int
    withholding_total: int
```

## 8. 의존성

- Python 3.11+ (StrEnum)
- pytest·ruff (dev)
- **외부 API X** (헌법 §14·offline)

## 9. 한계 (다음 cycle)

- 영수증 OCR (BYOK 옵션·다음 cycle)
- 매월 자동 import (구글 드라이브·다음 cycle)
- Streamlit UI
- 종합소득세 신고서 PDF 자동 (홈택스 양식)

## 10. 면책

- 본 도구 = 자기 측정 보조
- 세무사 자문 X·국세청 공식 신고 X
- 환급 추정 = 단순화·실제 = 누진세율·공제 다수
- 신고는 홈택스 또는 세무사 위임
