# 30-apps 스타트업 마스터 로드맵 (PO 명령 2026-05-08)

> PO 명령: "모든 플로우는 마치 스타트업 처럼 순서 맞춰서 계획대로 진행할것"
> 정합: ADR 0052·0053·0055·0056·0058·외부 research (Pieter Levels·Tony Dinh·Marc Lou)

## 0. 6 Phase 로드맵 (3년 캐시카우 ₩3,000만/월 목표)

```
Phase 1 (Cycle 85~90·Month 1)     IDEATION + CODE
Phase 2 (Cycle 90~100·Month 2~3)  POLISH + PRE-LAUNCH
Phase 3 (Cycle 100~120·Month 4~6) SOFT LAUNCH (PO 결정 시)
Phase 4 (Cycle 120~150·Month 7~12) MRR $1K (Habit Pixel 정합)
Phase 5 (Cycle 150~200·Year 2)    MRR $5K~10K (스케일)
Phase 6 (Year 3+)                  MRR ₩3,000만·캐시카우 자동
```

---

## Phase 1 — IDEATION + CODE (현재·진행 중)

### 1.1 ✅ 완료 (Cycle 85~88)
- [x] ADR 0052·0053·0054·0055·0056·0058 박제
- [x] 30 앱 매트릭스 (33 후보·6 카테고리)
- [x] 페인 게이트 시스템 (ADR 0055·자동 룰)
- [x] 5 앱 정식 진입 (kormarc·kdc·overtime·tax·sidehustle)
- [x] 1,407 tests passing (전체)
- [x] 외부 research 흡수 (P-series 17건·B2C 시장·인디 패턴)
- [x] _shared/payments wrapper template
- [x] _shared/legal_templates/privacy_policy_kr.md
- [x] _shared/AUTOMATIC_REVENUE_FLOW.md

### 1.2 ⏳ 남은 작업 (Cycle 89~90)
- [ ] _shared/auth/ Better Auth wrapper
- [ ] _shared/email/ Resend wrapper
- [ ] _shared/landing template (Streamlit 공용)
- [ ] _shared/legal_templates/{terms·refund} 추가
- [ ] 다음 캐시카우 후보 페인 발굴 (#33)

### 1.3 게이트 통과 조건 → Phase 2 진입
- [ ] ADR 0058 통과 앱 ≥ 2개 (현재 #31·#32 = 2개 ✅)
- [ ] _shared 5 모듈 완성 (payments·auth·email·landing·legal)
- [ ] 1,500+ tests passing
- [ ] 자동 수익화 플로우 8 단계 코드 준비

---

## Phase 2 — POLISH + PRE-LAUNCH (Month 2~3)

### 2.1 UX 깊이
- [ ] #31·#32 Streamlit UI 완성 (이미 v1·다음 = KWCAG 2.2 AA·Pretendard)
- [ ] 한국어 카피 정제 (Mom Test·persona-simulator·6 페르소나)
- [ ] FAQ 5개 (각 앱)·온보딩 3 step

### 2.2 결제 통합 dry-run
- [ ] PortOne sandbox·Stripe test mode·LS sandbox 모두 검증
- [ ] 영수증 자동 생성·세금계산서 (PortOne)·VAT 위임 (LS)
- [ ] 환불 7일 정책 코드 (전자상거래법 §17)

### 2.3 SEO + 콘텐츠 시드
- [ ] 각 앱 = 한국어 SEO 키워드 30개 매트릭스
- [ ] 블로그 시드 5편 (각 앱)·발행 = PO 결정 시
- [ ] X #buildinpublic 시드 7개 스레드 (PO 결정 시)

### 2.4 게이트 → Phase 3 진입
- [ ] PO 명시 "발사" 명령 (ADR 0052 활성 트리거)
- [ ] 사업자 등록·통신판매업 신고 완료 (PO 외부)
- [ ] PortOne v2 라이브 키 발급 (PO 외부)
- [ ] 처리방침·이용약관·환불정책 사업자정보 기입

---

## Phase 3 — SOFT LAUNCH (Month 4~6)

### 3.1 발사 (PO 결정 시·ADR 0058)
- [ ] Streamlit Cloud 배포 (₩0)·도메인 (₩15K/년)
- [ ] GitHub Pages 활성·README 영문/국문
- [ ] X 계정 + 첫 스레드 (founder 스토리)
- [ ] 한국 사이드 프로젝트 채널 발행 (디스콰이엇·GeekNews·Reddit)

### 3.2 조기 사용자 확보
- [ ] 14일 무료 체험 (Lean Startup)
- [ ] 조기 가입 100명 = Founding Member ₩4,950/월 (50% 영구·매출 성장 보고서 정합)
- [ ] Plausible 가입 + 4 funnel event 측정

### 3.3 5명 결제 게이트 (인디 정합)
- [ ] D+30: 결제 1+ = continue·0 = 채널 보강
- [ ] D+60: 결제 5+ = double-down·0~2 = 위험
- [ ] D+90: 결제 5+ = Phase 4·0~2 = archive 또는 maintenance

### 3.4 게이트 → Phase 4 진입
- [ ] 결제 ≥ 5명 (각 앱)
- [ ] MRR ≥ ₩50,000 (5 × ₩9,900)
- [ ] NPS ≥ 30·자발 추천 1+

---

## Phase 4 — MRR $1K (Month 7~12·Habit Pixel 벤치마크)

### 4.1 콘텐츠·SEO 누적
- [ ] 각 앱 = SEO 콘텐츠 50편 누적
- [ ] X 팔로워 1,000+
- [ ] 자발 추천 = viral coefficient ≥ 0.4

### 4.2 가격 최적화
- [ ] A/B 테스트 (₩4,900 vs ₩9,900 vs ₩14,900)
- [ ] 연 결제 할인 (45% off) 활성
- [ ] Founding Member 종료 → 정가 전환

### 4.3 다음 앱 launch (Lean Startup·1주 1앱)
- [ ] #33·#34·#35 = ADR 0055 통과 후 launch
- [ ] cross-link footer (Marc Lou 패턴)
- [ ] 동일 audience 재판매 (인디 정합)

### 4.4 게이트 → Phase 5
- [ ] MRR ≥ ₩1,000,000 ($750)
- [ ] 결제 ≥ 100명
- [ ] 30일 retention ≥ 60%

---

## Phase 5 — MRR $5K~10K (Year 2·스케일)

### 5.1 자동화 깊이
- [ ] CSAT 자동 (Resend webhook)
- [ ] 자동 환불 (전자상거래법 정합)
- [ ] 자동 영수증·세금계산서 (PortOne)
- [ ] CS 챗봇 (LLM 옵션·BYOK)

### 5.2 다국어 (글로벌)
- [ ] 영어 docs·UI (#31·#32 후보)
- [ ] 일본어 = NDL JAPAN/MARC 80% 호환 (외부 research·#1 kormarc-auto)

### 5.3 게이트 → Phase 6
- [ ] MRR ≥ ₩5,000,000 ($3,750)
- [ ] 30 앱 중 5+ = MRR ≥ ₩500K
- [ ] portfolio 매출 누적 ≥ ₩100,000,000

---

## Phase 6 — 캐시카우 자동 (Year 3+)

### 6.1 1인 PO 자동 운영
- [ ] 매월 1일 portfolio 자동 보고서 (P43L·이미 박제)
- [ ] 5명 룰 자동 archive 추천 (P44L)
- [ ] Q4 평가 자동 (P48L)

### 6.2 매각 또는 운영 결정
- [ ] 일부 앱 매각 (Marc Lou ZenVoice·ByeDispute 패턴·$10K~35K)
- [ ] 살아남은 앱 = double-down (광고·콘텐츠 2배)
- [ ] 다음 12개월 새 1~2 베팅

### 6.3 캐시카우 도달
- [ ] MRR ₩30,000,000+ (월 매출 3,000만)
- [ ] 1인 PO 자동 운영·시간 90% 자유
- [ ] 다음 베팅 자유롭게 (small bets·Daniel Vassallo)

---

## Phase별 시간 효율

| Phase | 기간 | Claude 자율 작업 | PO 외부 작업 |
|---|---|---|---|
| 1 | 1~2개월 | 5~10 cycles·코드 누적 | 0 (ADR 0052) |
| 2 | 1~2개월 | 5~7 cycles·UX·결제 sandbox | 사업자 등록 (선택) |
| 3 | 3개월 | 발사 후 모니터·콘텐츠 | 발사·홍보·결제 라이브 |
| 4 | 6개월 | 콘텐츠 50편·다음 앱 | A/B 테스트 결정 |
| 5 | 12개월 | 자동화·다국어 | 일부 매각 결정 |
| 6 | 12개월+ | 자동 운영·새 베팅 | 캐시카우 자유 |

## 게이트 정합

매 Phase 진입 = **이전 Phase 게이트 모두 충족**·미달 = Phase 유지·다음 cycle.

## 정합 정책

- ADR 0052 (코딩 외 X): Phase 1~2 = 정합·Phase 3+ = PO 명시 시
- ADR 0053 (30 앱): 매 Phase 1+ 신규 앱
- ADR 0055 (페인 게이트): 매 신규 = 4 단계 통과
- ADR 0056 (무한 자율): 매 응답 = Phase 진척
- ADR 0058 (조건부 배포): Phase 3 발사 시 = 4 조건 통과 의무
- 헌법 §3·§11·§14 = 모든 Phase 정합
