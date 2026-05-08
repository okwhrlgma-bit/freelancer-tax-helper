# 자동 수익화 플로우 (PO 명령 2026-05-08·30-apps 공유)

> ADR 0058 정합·캐시카우 검증 통과 앱 (#31·#32) 즉시 활성 가능
> 헌법 §3 (API 키 .env)·§14 (사용자 데이터 X)·§11 (raw % X) 정합

## 0. 핵심 흐름 (8 단계·완전 자동)

```
[1] 랜딩 방문 (SEO·콘텐츠·X #buildinpublic)
        ↓
[2] 무료 체험 (가입 X·바로 시도·헌법 §14 session_state)
        ↓
[3] "더 알아보기" 클릭 (제한 도달 시)
        ↓
[4] 가입 폼 (이메일만·소셜 로그인 X = 락인 회피)
        ↓
[5] 결제 (PortOne·Stripe·LS 자동 선택·국가별)
        ↓
[6] 환영 메일 자동 (Resend·activation key)
        ↓
[7] 사용 (offline·session_state·자관 데이터 X)
        ↓
[8] 자동 갱신 (월정액·14일 전 알림·1-click 취소)
```

## 1. 단계별 자동화 (각 앱 적용)

### Stage 1·2: 랜딩 + 무료 체험 (이미 완성)

- Streamlit `streamlit_app.py` (#31·#32 완성)
- session_state = 사용자 데이터·refresh = 휘발 (헌법 §14)
- 무료 체험 = 가입 X·즉시 사용

### Stage 3: 무료 → 유료 전환 트리거 (다음 cycle)

- 영수증 50건 / 시간 블록 100건 도달 시 = "더 보기 = ₩9,900/월" CTA
- 14일 무료 체험 (Lean Startup 정합)

### Stage 4: 가입 폼 (다음 cycle)

```python
# 30-apps/_shared/auth/__init__.py (다음 cycle)
@dataclass(frozen=True)
class SignupRequest:
    email: str
    consent_privacy: bool  # 처리방침 동의
    consent_marketing: bool = False  # 옵트인
```

- Better Auth (외부 research 권장·NextAuth 후속)
- 이메일만·소셜 로그인 X (락인 회피)

### Stage 5: 결제 (코드 준비 완료·_shared/payments)

```python
from _shared.payments import (
    PaymentConfig, CheckoutItem, select_provider, PRICE_BENCHMARKS_KRW,
)

config = PaymentConfig.from_env(select_provider("KR"))  # 국가별 자동
item = CheckoutItem(
    name="freelancer-tax-helper Pro",
    amount_krw=PRICE_BENCHMARKS_KRW["freelancer-tax-helper"],  # ₩9,900
    interval="monthly",
)
# config.is_configured() == True 시 결제 활성
```

PG 자동 선택:
- KR → PortOne v2 (한국 카드·세금계산서)
- US → Stripe (2.9%)
- 기타 → Lemon Squeezy (MoR·VAT 위임)

### Stage 6: 환영 메일 (다음 cycle·Resend)

```python
# _shared/email/welcome.py (다음 cycle)
@dataclass(frozen=True)
class WelcomeEmail:
    to_email: str
    app_name: str  # "freelancer-tax-helper" 등
    activation_key: str
    language: str = "ko"
```

- Resend 무료 (월 100통)·이후 $20/월
- 한국어 + 영어 2 템플릿

### Stage 7: 사용 (offline·완성)

- session_state = 휘발성 데이터 (헌법 §14)
- 사용자 컴퓨터에 export 옵션 (JSON·CSV)
- 자동 동기화 X (개인정보 보호)

### Stage 8: 갱신·이탈 방지 (다음 cycle)

- 14일 전 자동 갱신 알림 메일
- 1-click 취소 (한국 환불 No.1국 정합·DelightRoom)
- 월할 환불 정책 (전자상거래법 §17)
- 이탈 사유 1문항 설문 (옵트인·Mom Test 정합)

## 2. ADR 0058 통과 앱 즉시 활성 가능

| 앱 | PG | 가격 | 활성 조건 |
|---|---|---|---|
| #31 freelancer-tax-helper | PortOne (KR) | ₩9,900/월 | PO 사업자 등록 + PortOne 가입 |
| #32 sidehustle-tracker | PortOne (KR) | ₩4,900/월 | 동일 |

## 3. PO 외부 작업 (보류·ADR 0052)

자동화 가능·but PO 결정 시:
- ☐ Streamlit Cloud 배포 (5분·₩0)
- ☐ 도메인 구매 (₩15,000/년)
- ☐ PortOne v2 가입 + 키 발급
- ☐ Resend 가입 (이메일 발송)
- ☐ 사업자 등록 (홈택스·30분)
- ☐ 통신판매업 신고 (정부24·면허세 ₩40,500/년)

## 4. 매출 가설 (ADR 0058 통과 앱)

```
Month 1 (배포): 가입 100명·결제 3명 (3% 전환·인디 평균)
  매출 = 3 × ₩9,900 = ₩29,700/월

Month 6: 가입 500명·결제 25명 (5% 전환·SsJum 가이드 콘텐츠)
  매출 = 25 × ₩9,900 = ₩247,500/월

Month 12: 가입 2,000명·결제 100명 (5% 전환)
  매출 = 100 × ₩9,900 = ₩990,000/월 ≈ $750 MRR

→ Habit Pixel ($1K MRR/8개월) 정합·달성 가능
```

## 5. 캐시카우 도달 가설

```
Phase 1 (1~6개월): 코드·UI·docs 완성·발사 (PO 결정 시)
Phase 2 (6~12개월): MRR ₩100만·Habit Pixel 패턴 검증
Phase 3 (12~24개월): MRR ₩500만·캐시카우 본격 (1인 PO 자동 운영)
Phase 4 (24개월+): 30 앱 누적 = MRR ₩3,000만+
```

## 6. 정합 정책

- ADR 0052 (코딩 외 X): 코드 자율·외부 가입 = PO 결정 시
- ADR 0053 (30 앱): 모든 앱 = 본 플로우 적용
- ADR 0055 (페인 게이트): 통과 후만 본 플로우 활성
- ADR 0056 (무한 자율): 매 응답 = 본 플로우 강화
- ADR 0058 (조건부 배포): 4 조건 통과 시 = Stage 5+ 활성
- 헌법 §3·§11·§14 모두 정합

## 7. 다음 사이클 우선순위

1. _shared/auth/ Better Auth wrapper (Stage 4)
2. _shared/email/ Resend wrapper (Stage 6)
3. _shared/landing template (Streamlit + Stage 1)
4. _shared/billing/ 갱신·취소 wrapper (Stage 8)
5. 다음 캐시카우 후보 페인 발굴 (#33 후보·ADR 0055)
