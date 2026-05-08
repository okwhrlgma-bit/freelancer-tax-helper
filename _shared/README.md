# 30-apps 공유 자산 (`_shared/`)

> ADR 0058·0061·0066 정합·캐시카우 통과 앱 = 즉시 활성·packages/ 승격 (Sandi Metz AHA).
> v0.1.0·Apache-2.0·Python 3.11+·**Cycle 164 시점 = 자동화 + Bessemer KPI + 페인 검색 100% 완성·9 모듈·~89 자산**.

## 구성 (Cycle 104 → 142·8 모듈 + 4 markdown)

```
_shared/
├── auth/                     # 인증·검증·rate limit·audit chain (PIPA 5/5)
├── payments/                 # PortOne·Stripe·LS 3 wrapper + 수수료·환불·webhook
├── email_helper/             # 5/5 EmailType + 운영 KPI 자동 알림
├── landing/                  # Streamlit 12 컴포넌트 (KWCAG 2.2 AA)
├── onboarding/               # 체험·Founding·마일스톤·funnel KPI
├── legal_templates/          # privacy·terms·refund·cookie 4 markdown (PIPA)
├── AUTOMATIC_REVENUE_FLOW.md # 8 단계 수익화 흐름
├── STARTUP_ROADMAP.md        # 6 Phase·3년 ₩3,000만/월 목표
└── DEPLOYMENT_GUIDE.md       # PO 1시간 외부 작업 후 활성 절차
```

## helper 진화 (Cycle 104 → 164)

| Cycle | helper 수 | tests |
|---|---:|---:|
| 104 (정식) | ~15 | 9 |
| 124 (onboarding 신규) | ~20 | 24 |
| 131 (5/5 EmailType + 검증) | ~38 | 55 |
| 136 (환불·receipt_id) | ~46 | 82 |
| 142 (KPI·PII redact) | ~58 | 119 |
| 156 (analytics 신규·9 모듈) | ~78 | 212 |
| **164 (Bessemer KPI·ARPU·#4 reports)** | **~89** | **238** |

→ helper **5.9x**·tests **26.4x** (Cycle 104 → 164 누적·매우 견조).

## Bessemer Cloud Index 표준 KPI (Cycle 159·160·164 신규)

| KPI | helper | 임계 |
|---|---|---|
| ARPU | calculate_arpu_krw | base 계산 |
| LTV | calculate_ltv_krw | ≥ ₩50K |
| LTV/CAC | calculate_ltv_cac_ratio | ≥ 3 정상·≥ 5 우수 |
| Payback | calculate_payback_months | ≤ 12·≤ 6 우수 |
| Rule of 40 | calculate_rule_of_40 | ≥ 40·≥ 60 우수 |
| NRR | calculate_nrr_pct + diagnose_nrr | ≥ 100·≥ 110 우수 |
| Churn | calculate_churn_rate | B2C 5~10% |
| 통합 | format_bessemer_summary_kr | 5 KPI 한 줄·매주 PO 알림 |

## 자동화 흐름 100% (Cycle 142 시점)

| 영역 | helper | Cycle |
|---|---|---|
| 입력 검증 | validate_email + validate_password | 130 |
| 로그인 보안 | LoginRateLimiter (OWASP·KISA) | 134 |
| 로그 마스킹 | mask_email + redact_pii_for_log (PIPA) | 131·141 |
| 체험·Founding·마일스톤 | onboarding 모듈 (Habit Pixel 정합) | 124 |
| 결제 | idempotency·webhook 검증·receipt_id·fees·환불 | 139·137·136·129·135 |
| 이메일 5/5 + 운영 | welcome·receipt·renewal·cancel·reset·**weekly KPI** | 104·127·128·**142** |
| audit chain | AuditChain + AuditEntry (PIPA 5/5) | 138 |
| 운영 KPI | ConversionFunnel + diagnose_funnel | 140 |
| DRY UI | render_onboarding_bar (3 앱 통합) | 133 |
| 법무 4 markdown | privacy + terms + refund + cookie | 104·139 |

## 사용처 (Cycle 142 시점)

| # | 앱 | streamlit_app.py | _shared 통합 |
|---|---|---|---|
| 1 | kormarc-auto | (없음·Streamlit 미존재) | - |
| 2 | 책_KDC_분류 | (NO_GO 57·SKIP) | - |
| 4 | 사서_야근_추적 | ✅ (Cycle 132·154줄) | ✅ |
| 31 | 프리랜서_종소세_환급 | ✅ | ✅ |
| 32 | N잡_부업_시간_추적 | ✅ | ✅ |

→ 사용처 = **3** (Cycle 132 #4 추가)·5 도달 시 packages/ 승격 (ADR 0066).

## 벤치마크 (인디 사례·ADR 0058 정합)

| 사례 | 가격 | 패턴 |
|---|---|---|
| Habit Pixel ($1K MRR/8개월) | $5/월 | 단순 추적·구독 (#32 변형 정합) |
| Marc Lou ShipFast ($141K MRR) | lifetime $169 | boilerplate |
| Tony Dinh DevUtils ($45K MRR) | one-time $9 | 단일 기능 |
| 삼쩜삼 (한국 핀테크) | 환급 18.7% | 한국 niche (#31 변형 정합) |
| Pieter Levels PhotoAI ($132K MRR) | $24/월 | AI niche |

## 정합 정책

- ADR 0052 (코딩 외 X): 코드만 OK·외부 가입 = PO 결정 시
- ADR 0053 (30 앱): 모든 앱 = 본 _shared 활용
- ADR 0055 (페인 게이트): 통과 후 배포 가능
- ADR 0058 (조건부 배포): 4 조건 충족 시 발사 허용
- ADR 0061 (박제·코드 균형): 매 cycle = 코드 ≥50%
- ADR 0066 (5 사용처 packages/ 승격): Sandi Metz AHA

## 한국 법무 정합

- PIPA 5대 패턴 helper 5/5 정합 (Cycle 138 audit_chain 완성)
- 전자상거래법 §13 (영수증) + §17 (환불 7일) helper 자동
- 정보통신망법 §50의5 (쿠키 사전 동의) markdown 정합
- OWASP A07·KISA 권장 (LoginRateLimiter·HTTPS·SHA-256)
- RFC 5321 이메일 형식·NIST SP 800-63B 비밀번호 강도

## 외부 발사 시점 (PO 외부 작업 1시간 후)

```
1. 사업자 등록 (홈택스·30분·일반과세자·SW업)
2. 통신판매업 신고 (정부24·면허세 ₩40,500/년)
3. PortOne v2 가입 (1시간·sandbox→production 1주)
4. Streamlit Cloud 배포 (5분·₩0)
5. .env 키 입력 (RESEND·PORTONE·ANTHROPIC) → Secrets

→ 자동 운영 즉시 활성:
   - 가입·결제·환불·이메일·audit·KPI 모두 helper 자동
   - PO = 매주 KPI 메일 1통만 확인
```
