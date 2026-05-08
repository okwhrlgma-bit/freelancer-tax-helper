# 30-apps 배포 가이드 (Cycle 117·PO 결정 시 1시간 활성)

> ADR 0058 통과 앱 (#31·#32) = PO 외부 작업 1시간 = 매출 가능 활성.

## 0. 사전 준비 (PO 외부·1회)

### Step 1: 사업자 등록 (30분·홈택스)

1. https://hometax.go.kr → 증명·등록·신청 → 사업자등록 신청
2. 업종: 722000 응용 소프트웨어 개발 (정보통신업)
3. 사업장: 자택
4. **일반과세자** 선택 (간이 X·세금계산서 발급 가능)
5. 처리: 2~3 영업일·사업개시일로부터 20일 내 신청 의무

### Step 2: 통신판매업 신고 (1주 내·정부24)

1. https://gov.kr → 통신판매업 신고
2. 면허세 ₩40,500/년 (1월 정기분)
3. 선행: PG 가입 후 구매안전서비스 이용확인증

### Step 3: PortOne v2 가입 (1시간)

1. https://portone.io · 사업자등록번호 입력
2. API Key·Secret Key·Webhook Secret 발급
3. 카드사 심사 (1주)·체크카드·세금계산서 자동
4. **sandbox 먼저 검증·이후 production**

### Step 4: Streamlit Cloud 가입 (5분·₩0)

1. https://share.streamlit.io · GitHub 연동
2. New app → repo·main file = streamlit_app.py
3. Settings → Secrets → `.env.example` 복사·실 키 입력
4. Deploy → URL 자동 발급

## 1. 앱별 배포 단계

### #31 31_프리랜서_종소세_환급 (출시명 = freelancer-tax-helper)

```bash
cd 30-apps/31_프리랜서_종소세_환급
# 1. .env 생성 (.env.example 복사·실 키 입력)
cp .env.example .env
# 2. 로컬 테스트
pip install -e .
streamlit run streamlit_app.py
# 3. 독립 git repo 변환 (PO 외부)
git init && git add -A
git commit -m "feat: initial freelancer-tax-helper v0.1.0"
gh repo create freelancer-tax-helper --public
git push -u origin main
# 4. Streamlit Cloud · Secrets에 .env 내용 복사 → Deploy
```

URL: `https://freelancer-tax-helper.streamlit.app` 또는 도메인.

> **참고**: 폴더명 = 한국어 (PO 인식)·GitHub repo·Streamlit URL = 영문 (외부 표준).

### #32 32_N잡_부업_시간_추적 (출시명 = sidehustle-tracker)

(동일 패턴·`gh repo create sidehustle-tracker --public`)

URL: `https://sidehustle-tracker.streamlit.app`

## 2. 배포 후 (자동 매출 활성화)

### Step 1: 가격 페이지 활성

- `_shared/landing/streamlit_helper.render_pricing_card`
- 14일 무료 체험·월 ₩4,900~9,900

### Step 2: 결제 wrapper 활성

- `_shared/payments/PaymentConfig.from_env()`
- PortOne sandbox → production 전환 (사업자 등록 후)

### Step 3: 이메일 자동

- `_shared/email_helper/build_welcome_message`
- Resend API · 환영·영수증·갱신 알림 자동

### Step 4: 법무 3 문서

- `_shared/legal_templates/{privacy_policy·terms_of_service·refund_policy}_kr.md`
- 사업자 정보 기입·footer 노출

## 3. 비용 추정 (1년)

| 항목 | 비용 |
|---|---|
| 사업자 등록·통신판매 | 면허세 ₩40,500/년 |
| 도메인 | ₩15,000/년 |
| Streamlit Cloud | ₩0 (Community) |
| Resend (월 100통) | ₩0·이후 $20/월 |
| PortOne 수수료 | 매출의 약 2.5~3.5% |
| **합** | **약 ₩50K/년 + 수수료** |

## 4. 매출 가설 (Phase 1~2)

```
Month 1: 가입 100명 → 결제 3명 (3% 전환)
  매출 = 3 × ₩9,900 = ₩29,700/월
Month 6: 가입 500명 → 결제 25명 (5%)
  매출 = ₩247,500/월
Month 12: 가입 2,000명 → 결제 100명
  매출 = ₩990,000/월 ≈ $750 MRR
```

→ Habit Pixel ($1K MRR/8개월) 정합·달성 가능 (벤치마크 ADR 0058).

## 5. PO 명시 명령 시 활성 (자율)

```
"발사 시작" → ADR 0052 활성 트리거 발동
"Streamlit 배포" → 위 Step 4 즉시 진행
"PortOne 활성" → Step 3 진행
```

## 6. 정합 정책

- ADR 0052 (코딩 외 X) = 부분 supersede
- ADR 0058 (캐시카우 통과 앱 배포 허용) = #31·#32 정합
- ADR 0064 (PO 사전 동의) = "발사 시작" 명시 시
- 헌법 §3 (env only)·§14 (사용자 컴퓨터)
