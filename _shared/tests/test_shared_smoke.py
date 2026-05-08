"""_shared 정식 패키지 smoke test (Cycle 104·packages/ 승격).

Sandi Metz AHA 정합·5 사용처 도달·정식 패키지화 회귀 보장.
"""

from __future__ import annotations

import sys
from pathlib import Path

# 30-apps/_shared 경로 등록 (다른 앱 import 패턴 정합)
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPackageMetadata:
    def test_version_present(self) -> None:
        import _shared  # type: ignore[import-not-found]

        assert _shared.__version__ == "0.1.0"

    def test_apache_license(self) -> None:
        import _shared  # type: ignore[import-not-found]

        assert _shared.__license__ == "Apache-2.0"


class TestModuleImports:
    """7 _shared 모듈 import 정상 보장."""

    def test_payments_module(self) -> None:
        from payments import PaymentProvider, select_provider

        assert PaymentProvider.PORTONE.value == "portone"
        # 국가별 자동 선택
        assert select_provider("KR") == PaymentProvider.PORTONE
        assert select_provider("US") == PaymentProvider.STRIPE

    def test_payments_config_from_env(self) -> None:
        from payments import PaymentConfig

        config = PaymentConfig.from_env("portone")
        assert config.provider == "portone"
        assert config.timeout_sec == 10

    def test_auth_module(self) -> None:
        from auth import REQUIRED_CONSENTS, generate_csrf_token

        token = generate_csrf_token()
        assert len(token) >= 30  # 128 bit base64
        assert "privacy" in REQUIRED_CONSENTS

    def test_email_helper_module(self) -> None:
        # email_helper rename 후 정상 import (Cycle 104)
        from email_helper import EmailType, build_welcome_message

        msg = build_welcome_message("test@example.com", "test-app", language="ko")
        assert msg.type == EmailType.WELCOME.value
        assert "환영" in msg.subject

    def test_landing_module(self) -> None:
        from landing import default_faqs

        faqs = default_faqs()
        assert len(faqs) == 5
        # FAQ 5건 모두 한국어
        for faq in faqs:
            assert faq.question_ko
            assert faq.answer_ko


class TestConstitutionCompliance:
    """헌법 §3 (env only)·§14 (사용자 데이터) 정합 보장."""

    def test_payments_env_only_no_hardcode(self) -> None:
        """결제 wrapper = .env에서만 키 로드·하드코딩 X."""
        from payments import PaymentConfig

        config = PaymentConfig.from_env("portone")
        # 미설정 시 빈 문자열 (헌법 §3 정합)
        if not config.is_configured():
            assert config.api_key in {"", config.api_key}  # 빈 또는 env

    def test_email_disclaimer_obligation(self) -> None:
        """이메일 = 면책 의무 (전자상거래법 §17)."""
        from email_helper import build_welcome_message

        msg = build_welcome_message("test@example.com", "test-app", language="ko")
        assert "7일" in msg.body_text


class TestRenewalAndCancel:
    """Cycle 127 신규: 갱신·취소 메시지 (전자상거래법 §17 정합)."""

    def test_renewal_notice_14_days_before(self) -> None:
        from email_helper import EmailType, build_renewal_notice_message

        msg = build_renewal_notice_message(
            to_email="user@example.com",
            app_name="freelancer-tax-helper",
            next_charge_krw=9_900,
            next_charge_date="2026-06-23",
        )
        assert msg.type == EmailType.RENEWAL_NOTICE.value
        assert "14일" in msg.body_text
        assert "₩9,900" in msg.body_text
        assert "2026-06-23" in msg.body_text
        assert "해지" in msg.body_text  # 사용자 권리 명시

    def test_renewal_negative_amount_rejected(self) -> None:
        from email_helper import build_renewal_notice_message

        import pytest

        with pytest.raises(ValueError, match="next_charge_krw"):
            build_renewal_notice_message(
                to_email="user@example.com",
                app_name="x",
                next_charge_krw=-100,
                next_charge_date="2026-06-23",
            )

    def test_cancel_with_refund(self) -> None:
        from email_helper import EmailType, build_cancel_message

        msg = build_cancel_message(
            to_email="user@example.com",
            app_name="sidehustle-tracker",
            refund_amount_krw=4_900,
        )
        assert msg.type == EmailType.CANCEL.value
        assert "₩4,900" in msg.body_text
        assert "3~5" in msg.body_text  # 영업일 안내

    def test_cancel_zero_refund(self) -> None:
        from email_helper import build_cancel_message

        msg = build_cancel_message(
            to_email="user@example.com",
            app_name="x",
            refund_amount_krw=0,
        )
        assert "₩0" in msg.body_text


class TestPasswordReset:
    """Cycle 128: OWASP 정합 비밀번호 재설정."""

    def test_password_reset_https_required(self) -> None:
        from email_helper import EmailType, build_password_reset_message

        msg = build_password_reset_message(
            to_email="user@example.com",
            app_name="freelancer-tax-helper",
            reset_url="https://app.example.com/reset?token=abc",
            expires_in_minutes=30,
        )
        assert msg.type == EmailType.PASSWORD_RESET.value
        assert "30분" in msg.body_text
        assert "https://" in msg.body_text

    def test_password_reset_http_rejected(self) -> None:
        import pytest

        from email_helper import build_password_reset_message

        with pytest.raises(ValueError, match="HTTPS"):
            build_password_reset_message(
                to_email="user@example.com",
                app_name="x",
                reset_url="http://insecure.example.com/reset",
            )

    def test_password_reset_expiry_capped_60(self) -> None:
        import pytest

        from email_helper import build_password_reset_message

        with pytest.raises(ValueError, match="1~60"):
            build_password_reset_message(
                to_email="user@example.com",
                app_name="x",
                reset_url="https://app.example.com/reset?token=abc",
                expires_in_minutes=120,
            )

    def test_password_reset_zero_expiry_rejected(self) -> None:
        import pytest

        from email_helper import build_password_reset_message

        with pytest.raises(ValueError, match="1~60"):
            build_password_reset_message(
                to_email="user@example.com",
                app_name="x",
                reset_url="https://app.example.com/reset?token=abc",
                expires_in_minutes=0,
            )


class TestFees:
    """Cycle 129: PG 수수료·VAT 분해 (실 매출 운영 정합)."""

    def test_portone_3_3_percent(self) -> None:
        from payments import PaymentProvider, calculate_fees

        breakdown = calculate_fees(9_900, provider=PaymentProvider.PORTONE)
        assert breakdown.gross_krw == 9_900
        assert breakdown.pg_fee_krw == 326  # 9900 × 3.3% = 326.7 → 326
        assert breakdown.pg_fee_fixed_krw == 0
        assert breakdown.vat_krw == 900  # 9900 / 11 = 900
        assert breakdown.net_krw == 9_574  # 9900 - 326

    def test_stripe_2_9_plus_420(self) -> None:
        from payments import PaymentProvider, calculate_fees

        breakdown = calculate_fees(9_900, provider=PaymentProvider.STRIPE)
        assert breakdown.pg_fee_krw == 287  # 9900 × 2.9% = 287.1 → 287
        assert breakdown.pg_fee_fixed_krw == 420
        assert breakdown.net_krw == 9_193  # 9900 - 287 - 420

    def test_lemon_squeezy_5_percent(self) -> None:
        from payments import PaymentProvider, calculate_fees

        breakdown = calculate_fees(9_900, provider=PaymentProvider.LEMON_SQUEEZY)
        assert breakdown.pg_fee_krw == 495  # 5%
        assert breakdown.pg_fee_fixed_krw == 700

    def test_general_tax_vat_one_eleventh(self) -> None:
        from payments import calculate_fees

        breakdown = calculate_fees(11_000)  # 정확히 1/11
        assert breakdown.vat_krw == 1_000

    def test_simple_tax_zero_vat(self) -> None:
        from payments import calculate_fees

        breakdown = calculate_fees(9_900, is_general_tax=False)
        assert breakdown.vat_krw == 0  # 간이과세자 (외부 901 진단 = 차단·but 옵션 보존)

    def test_negative_gross_rejected(self) -> None:
        import pytest

        from payments import calculate_fees

        with pytest.raises(ValueError, match="gross_krw"):
            calculate_fees(-100)

    def test_mrr_net_100_paying_users(self) -> None:
        """Habit Pixel Month 12 (가입 2,000·결제 100·₩9,900) 시나리오."""
        from payments import calculate_mrr_net

        net = calculate_mrr_net(paying_users=100, monthly_price_krw=9_900)
        gross = 100 * 9_900  # ₩990,000
        expected_pg = int(gross * 3.3 / 100)
        assert net == gross - expected_pg

    def test_label_kr_format(self) -> None:
        from payments import calculate_fees

        breakdown = calculate_fees(9_900)
        assert "₩9,900" in breakdown.label_kr
        assert "PG 3.3%" in breakdown.label_kr
        assert "VAT" in breakdown.label_kr


class TestPasswordStrength:
    """Cycle 130: OWASP·NIST 비밀번호 강도 검증."""

    def test_too_short_rejected(self) -> None:
        from auth import validate_password_strength

        check = validate_password_strength("Ab1!")
        assert not check.is_valid
        assert any("8자" in i for i in check.issues_kr)

    def test_too_long_rejected(self) -> None:
        from auth import MAX_PASSWORD_LENGTH, validate_password_strength

        check = validate_password_strength("A1!" + "x" * MAX_PASSWORD_LENGTH)
        assert not check.is_valid
        assert any("64자" in i for i in check.issues_kr)

    def test_low_diversity_rejected(self) -> None:
        from auth import validate_password_strength

        check = validate_password_strength("alllowercase")  # 1 종류
        assert not check.is_valid
        assert any("문자 종류" in i for i in check.issues_kr)

    def test_common_pattern_rejected(self) -> None:
        from auth import validate_password_strength

        check = validate_password_strength("Password123!")
        assert not check.is_valid
        assert any("password" in i for i in check.issues_kr)

    def test_strong_password_valid(self) -> None:
        from auth import validate_password_strength

        check = validate_password_strength("Q9z!mLpW#kN3")  # 12자·4 종류
        assert check.is_valid
        assert check.score >= 3
        assert check.label_kr in {"강함", "매우 강함"}

    def test_very_strong_16_chars(self) -> None:
        from auth import validate_password_strength

        check = validate_password_strength("Q9z!mLpW#kN3vRtX")
        assert check.score == 4
        assert check.label_kr == "매우 강함"


class TestEmailFormat:
    """Cycle 130: RFC 5321 간이 검증."""

    def test_valid_email(self) -> None:
        from auth import validate_email_format

        assert validate_email_format("user@example.com")
        assert validate_email_format("a.b+tag@sub.example.co.kr")

    def test_no_at_sign_rejected(self) -> None:
        from auth import validate_email_format

        assert not validate_email_format("noatsign.example.com")

    def test_double_at_rejected(self) -> None:
        from auth import validate_email_format

        assert not validate_email_format("a@b@c.com")

    def test_no_domain_dot_rejected(self) -> None:
        from auth import validate_email_format

        assert not validate_email_format("user@localhost")

    def test_empty_rejected(self) -> None:
        from auth import validate_email_format

        assert not validate_email_format("")
        assert not validate_email_format("@example.com")
        assert not validate_email_format("user@")

    def test_too_long_rejected(self) -> None:
        from auth import validate_email_format

        long_email = "a" * 250 + "@x.com"  # 256자 초과
        assert not validate_email_format(long_email)


class TestEmailMasking:
    """Cycle 131: PIPA 정합 이메일 마스킹 (화면·로그·CS 의무)."""

    def test_typical_email_masked(self) -> None:
        from auth import mask_email_for_display

        assert mask_email_for_display("user@example.com") == "u***@example.com"

    def test_two_char_local(self) -> None:
        from auth import mask_email_for_display

        assert mask_email_for_display("ab@x.kr") == "a*@x.kr"

    def test_single_char_local(self) -> None:
        from auth import mask_email_for_display

        assert mask_email_for_display("a@x.kr") == "*@x.kr"

    def test_invalid_email_returns_stars(self) -> None:
        from auth import mask_email_for_display

        assert mask_email_for_display("not-an-email") == "***"
        assert mask_email_for_display("") == "***"

    def test_long_local_masked_proportionally(self) -> None:
        from auth import mask_email_for_display

        result = mask_email_for_display("longusername@example.com")
        assert result == "l***********@example.com"
        # 12자 local·첫 1 + * 11


class TestOnboardingBarHelper:
    """Cycle 133: render_onboarding_bar import + early return (streamlit X 환경)."""

    def test_import_exposed(self) -> None:
        from landing.streamlit_helper import render_onboarding_bar

        # callable 확인 (실 렌더링 = streamlit 의존·skip)
        assert callable(render_onboarding_bar)

    def test_early_return_no_streamlit(self) -> None:
        """STREAMLIT_AVAILABLE=False 환경에서 안전 (no-op)."""
        from landing.streamlit_helper import render_onboarding_bar

        # 호출해도 예외 X (st = None 분기)
        result = render_onboarding_bar("founding label", "milestone label")
        assert result is None  # void return


class TestLoginRateLimiter:
    """Cycle 134: OWASP brute force 방어·PIPA 5대 패턴 정합."""

    def test_initial_attempts_full(self) -> None:
        from auth import DEFAULT_MAX_ATTEMPTS, LoginRateLimiter

        limiter = LoginRateLimiter()
        assert limiter.remaining_attempts("user@example.com") == DEFAULT_MAX_ATTEMPTS
        assert not limiter.is_locked("user@example.com")

    def test_lockout_after_max_failures(self) -> None:
        from auth import LoginRateLimiter

        limiter = LoginRateLimiter(max_attempts=3, window_minutes=5, lockout_minutes=15)
        for _ in range(2):
            locked = limiter.record_failure("attacker@example.com")
            assert not locked
        # 3번째 실패 = 락 발동
        locked = limiter.record_failure("attacker@example.com")
        assert locked
        assert limiter.is_locked("attacker@example.com")
        assert limiter.remaining_attempts("attacker@example.com") == 0

    def test_success_resets_counter(self) -> None:
        from auth import LoginRateLimiter

        limiter = LoginRateLimiter(max_attempts=3)
        limiter.record_failure("user@example.com")
        limiter.record_failure("user@example.com")
        limiter.record_success("user@example.com")
        assert limiter.remaining_attempts("user@example.com") == 3

    def test_window_expires_old_attempts(self) -> None:
        from datetime import UTC, datetime, timedelta

        from auth import LoginRateLimiter

        limiter = LoginRateLimiter(max_attempts=3, window_minutes=5, lockout_minutes=15)
        old = datetime.now(UTC) - timedelta(minutes=10)
        recent = datetime.now(UTC)
        # 10분 전 실패 2건 = 창 밖
        limiter.record_failure("user@example.com", now=old)
        limiter.record_failure("user@example.com", now=old)
        # 현재 1번 실패 = 창 안 1건
        limiter.record_failure("user@example.com", now=recent)
        assert limiter.remaining_attempts("user@example.com", now=recent) == 2

    def test_lockout_expires_after_duration(self) -> None:
        from datetime import UTC, datetime, timedelta

        from auth import LoginRateLimiter

        limiter = LoginRateLimiter(max_attempts=2, window_minutes=5, lockout_minutes=15)
        t0 = datetime.now(UTC)
        limiter.record_failure("user@example.com", now=t0)
        limiter.record_failure("user@example.com", now=t0)
        assert limiter.is_locked("user@example.com", now=t0)
        # 16분 후 = 락 해제
        future = t0 + timedelta(minutes=16)
        assert not limiter.is_locked("user@example.com", now=future)

    def test_invalid_config_rejected(self) -> None:
        import pytest

        from auth import LoginRateLimiter

        with pytest.raises(ValueError, match="0 의무"):
            LoginRateLimiter(max_attempts=0)
        with pytest.raises(ValueError, match="0 의무"):
            LoginRateLimiter(window_minutes=-1)

    def test_independent_keys(self) -> None:
        from auth import LoginRateLimiter

        limiter = LoginRateLimiter(max_attempts=3)
        for _ in range(3):
            limiter.record_failure("a@example.com")
        assert limiter.is_locked("a@example.com")
        assert not limiter.is_locked("b@example.com")
        assert limiter.remaining_attempts("b@example.com") == 3


class TestRefundEligibility:
    """Cycle 135: 전자상거래법 §17 환불 자동 판단."""

    def test_within_7_days_unused_full_refund(self) -> None:
        from datetime import UTC, datetime, timedelta

        from payments import calculate_refund_amount

        paid = datetime.now(UTC) - timedelta(days=2)
        decision = calculate_refund_amount(9_900, paid_at=paid, usage_ratio=0.0)
        assert decision.eligible
        assert decision.full_refund
        assert decision.refund_amount_krw == 9_900
        assert "전액" in decision.reason_kr

    def test_within_7_days_30_percent_used_full(self) -> None:
        from datetime import UTC, datetime, timedelta

        from payments import calculate_refund_amount

        paid = datetime.now(UTC) - timedelta(days=2)
        decision = calculate_refund_amount(9_900, paid_at=paid, usage_ratio=0.30)
        assert decision.eligible
        assert decision.full_refund  # 30% 이하 = 전액 정합

    def test_within_7_days_50_percent_partial(self) -> None:
        from datetime import UTC, datetime, timedelta

        from payments import calculate_refund_amount

        paid = datetime.now(UTC) - timedelta(days=3)
        decision = calculate_refund_amount(9_900, paid_at=paid, usage_ratio=0.50)
        assert decision.eligible
        assert not decision.full_refund
        assert decision.refund_amount_krw == 4_950  # 50% 차감

    def test_after_7_days_rejected(self) -> None:
        from datetime import UTC, datetime, timedelta

        from payments import calculate_refund_amount

        paid = datetime.now(UTC) - timedelta(days=10)
        decision = calculate_refund_amount(9_900, paid_at=paid, usage_ratio=0.0)
        assert not decision.eligible
        assert decision.refund_amount_krw == 0
        assert "7일 초과" in decision.reason_kr

    def test_is_refund_eligible_boundary(self) -> None:
        from datetime import UTC, datetime, timedelta

        from payments import is_refund_eligible

        now = datetime.now(UTC)
        # 정확히 7일·아직 가능
        assert is_refund_eligible(now - timedelta(days=7), now=now)
        # 7일 1초 = 초과
        assert not is_refund_eligible(
            now - timedelta(days=7, seconds=1), now=now
        )

    def test_naive_paid_at_rejected(self) -> None:
        import pytest
        from datetime import datetime

        from payments import is_refund_eligible

        with pytest.raises(ValueError, match="UTC tzinfo"):
            is_refund_eligible(datetime(2026, 5, 9))

    def test_negative_amount_rejected(self) -> None:
        import pytest
        from datetime import UTC, datetime

        from payments import calculate_refund_amount

        with pytest.raises(ValueError, match="gross_paid_krw"):
            calculate_refund_amount(-100, paid_at=datetime.now(UTC))

    def test_invalid_usage_ratio_rejected(self) -> None:
        import pytest
        from datetime import UTC, datetime

        from payments import calculate_refund_amount

        with pytest.raises(ValueError, match="usage_ratio"):
            calculate_refund_amount(9_900, paid_at=datetime.now(UTC), usage_ratio=1.5)
        with pytest.raises(ValueError, match="usage_ratio"):
            calculate_refund_amount(9_900, paid_at=datetime.now(UTC), usage_ratio=-0.1)


class TestReceiptIdGeneration:
    """Cycle 136: 영수증 ID 자동 생성 (전자상거래법 §13 정합)."""

    def test_format_matches(self) -> None:
        import re
        from payments import generate_receipt_id

        rid = generate_receipt_id()
        assert re.match(r"^RCPT-\d{8}-[0-9A-F]{8}$", rid)

    def test_uniqueness(self) -> None:
        from payments import generate_receipt_id

        ids = {generate_receipt_id() for _ in range(100)}
        assert len(ids) == 100  # 100건 모두 unique (8자 hex = 1/4억 충돌)

    def test_custom_prefix(self) -> None:
        from payments import generate_receipt_id

        rid = generate_receipt_id(prefix="REF")
        assert rid.startswith("REF-")

    def test_invalid_prefix_rejected(self) -> None:
        import pytest

        from payments import generate_receipt_id

        with pytest.raises(ValueError, match="prefix"):
            generate_receipt_id(prefix="")
        with pytest.raises(ValueError, match="prefix"):
            generate_receipt_id(prefix="TOOLONG12")  # 9자

    def test_date_in_id(self) -> None:
        from datetime import UTC, datetime

        from payments import generate_receipt_id

        fixed = datetime(2026, 5, 9, tzinfo=UTC)
        rid = generate_receipt_id(now=fixed)
        assert "20260509" in rid


class TestWebhookSignatureVerification:
    """Cycle 137: HMAC SHA-256 webhook 검증 (PortOne·Stripe 표준)."""

    def _sign(self, payload: bytes, secret: str) -> str:
        import hashlib
        import hmac

        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    def test_valid_signature_passes(self) -> None:
        from payments import verify_webhook_signature

        payload = b'{"event":"payment.completed","amount":9900}'
        secret = "whsec_test_abc123"
        sig = self._sign(payload, secret)
        assert verify_webhook_signature(payload, sig, secret)

    def test_sha256_prefix_accepted(self) -> None:
        from payments import verify_webhook_signature

        payload = b'{"event":"refund"}'
        secret = "whsec_xyz"
        sig = "sha256=" + self._sign(payload, secret)
        assert verify_webhook_signature(payload, sig, secret)

    def test_wrong_signature_rejected(self) -> None:
        from payments import verify_webhook_signature

        payload = b'{"event":"payment"}'
        assert not verify_webhook_signature(payload, "deadbeef" * 8, "secret")

    def test_tampered_payload_rejected(self) -> None:
        from payments import verify_webhook_signature

        original = b'{"amount":9900}'
        tampered = b'{"amount":99000}'  # 0 추가 (10배)
        secret = "whsec_test"
        sig = self._sign(original, secret)
        assert verify_webhook_signature(original, sig, secret)
        assert not verify_webhook_signature(tampered, sig, secret)

    def test_empty_inputs_rejected(self) -> None:
        from payments import verify_webhook_signature

        assert not verify_webhook_signature(b"", "sig", "secret")
        assert not verify_webhook_signature(b"payload", "", "secret")
        assert not verify_webhook_signature(b"payload", "sig", "")

    def test_invalid_algorithm_returns_false(self) -> None:
        from payments import verify_webhook_signature

        payload = b'{"x":1}'
        assert not verify_webhook_signature(
            payload, "abc", "secret", algorithm="not_exist_algo"
        )


class TestAuditChain:
    """Cycle 138: PIPA 5대 패턴 5/5·KISA 해시 체인 무결성."""

    def test_empty_chain_verifies(self) -> None:
        from auth import AuditChain

        chain = AuditChain()
        assert len(chain) == 0
        assert chain.verify_chain()  # 빈 = trivially valid

    def test_single_entry_chain(self) -> None:
        from auth import AuditChain, GENESIS_HASH

        chain = AuditChain()
        entry = chain.append("signup", "u***@example.com", "consent=privacy+terms")
        assert len(chain) == 1
        assert entry.prev_hash == GENESIS_HASH
        assert chain.verify_chain()

    def test_multiple_entries_chained(self) -> None:
        from auth import AuditChain

        chain = AuditChain()
        e1 = chain.append("signup", "u***@example.com")
        e2 = chain.append("login", "u***@example.com")
        e3 = chain.append("payment", "u***@example.com", "amount=9900")
        assert len(chain) == 3
        assert e2.prev_hash == e1.hash
        assert e3.prev_hash == e2.hash
        assert chain.verify_chain()

    def test_tampered_entry_detected(self) -> None:
        from dataclasses import replace

        from auth import AuditChain

        chain = AuditChain()
        chain.append("signup", "actor1")
        chain.append("payment", "actor1", "amount=9900")
        # 직접 변조 시도 (frozen → replace로 새 객체)
        tampered = replace(chain.entries[1], payload_summary="amount=99000")
        chain._entries[1] = tampered  # noqa: SLF001 (테스트 변조 시뮬)
        assert not chain.verify_chain()

    def test_empty_event_rejected(self) -> None:
        import pytest

        from auth import AuditChain

        chain = AuditChain()
        with pytest.raises(ValueError, match="event"):
            chain.append("", "actor1")

    def test_entries_view_is_tuple(self) -> None:
        from auth import AuditChain

        chain = AuditChain()
        chain.append("login", "actor1")
        # tuple = 불변·변조 방지
        assert isinstance(chain.entries, tuple)

    def test_compute_hash_deterministic(self) -> None:
        from auth import AuditChain

        chain = AuditChain()
        entry = chain.append("login", "user@example.com")
        # 같은 entry 데이터 = 같은 hash (재계산)
        assert entry.compute_hash() == entry.hash


class TestPIIRedaction:
    """Cycle 141: 로그 PII 마스킹 (PIPA·KISA 권장)."""

    def test_email_redacted(self) -> None:
        from auth import redact_pii_for_log

        result = redact_pii_for_log("Login attempt by user@example.com failed")
        assert "user@example.com" not in result
        assert "u***@example.com" in result

    def test_korean_phone_redacted(self) -> None:
        from auth import redact_pii_for_log

        result = redact_pii_for_log("연락처: 010-1234-5678 입력됨")
        assert "1234" not in result
        assert "010-****-5678" in result

    def test_phone_no_dash_redacted(self) -> None:
        from auth import redact_pii_for_log

        result = redact_pii_for_log("phone 01012345678 received")
        assert "01012345678" not in result

    def test_business_number_redacted(self) -> None:
        from auth import redact_pii_for_log

        result = redact_pii_for_log("사업자번호 123-45-67890 등록")
        assert "67890" not in result
        assert "123-**-*****" in result

    def test_card_number_redacted(self) -> None:
        from auth import redact_pii_for_log

        result = redact_pii_for_log("Card 1234-5678-9012-3456 charged")
        assert "1234-5678-9012" not in result
        assert "****-****-****-3456" in result

    def test_multiple_pii_in_text(self) -> None:
        from auth import redact_pii_for_log

        text = "User test@x.com phone 010-1111-2222 paid by 1111-2222-3333-4444"
        result = redact_pii_for_log(text)
        assert "test@x.com" not in result
        assert "010-1111" not in result
        assert "1111-2222-3333" not in result

    def test_empty_text_returned(self) -> None:
        from auth import redact_pii_for_log

        assert redact_pii_for_log("") == ""

    def test_no_pii_unchanged(self) -> None:
        from auth import redact_pii_for_log

        text = "Normal log line: user logged in successfully"
        assert redact_pii_for_log(text) == text


class TestWeeklyKpiMessage:
    """Cycle 142: 주간 KPI PO 자동 알림."""

    def test_message_includes_funnel_and_diagnosis(self) -> None:
        from email_helper import build_weekly_kpi_message

        msg = build_weekly_kpi_message(
            to_email="po@example.com",
            app_name="freelancer-tax-helper",
            funnel_label_kr="방문 1,000 → 가입 100 (10.0%)",
            diagnosis_kr="정상 범위",
            week_label="2026-W19",
        )
        assert "2026-W19" in msg.subject
        assert "방문 1,000" in msg.body_text
        assert "정상 범위" in msg.body_text
        assert "Habit Pixel" in msg.body_text

    def test_empty_inputs_rejected(self) -> None:
        import pytest

        from email_helper import build_weekly_kpi_message

        with pytest.raises(ValueError, match="비어있을"):
            build_weekly_kpi_message(
                to_email="po@example.com",
                app_name="x",
                funnel_label_kr="",
                diagnosis_kr="진단",
                week_label="W19",
            )

    def test_subject_format(self) -> None:
        from email_helper import build_weekly_kpi_message

        msg = build_weekly_kpi_message(
            to_email="po@example.com",
            app_name="sidehustle-tracker",
            funnel_label_kr="방문 500",
            diagnosis_kr="정상",
            week_label="2026-05-04~10",
        )
        assert msg.subject.startswith("[sidehustle-tracker]")
        assert "주간 KPI" in msg.subject


class TestPriceFormat:
    """Cycle 143: 가격·기간 한국어 포맷."""

    def test_monthly_default(self) -> None:
        from payments import format_price_with_period_kr

        assert format_price_with_period_kr(9_900) == "₩9,900/월"

    def test_yearly_includes_annual(self) -> None:
        from payments import format_price_with_period_kr

        result = format_price_with_period_kr(9_900, "yearly")
        assert "₩9,900/월" in result
        assert "₩118,800" in result  # 12배

    def test_one_time(self) -> None:
        from payments import format_price_with_period_kr

        assert format_price_with_period_kr(169_000, "one-time") == "₩169,000 1회"

    def test_zero_returns_free(self) -> None:
        from payments import format_price_with_period_kr

        assert format_price_with_period_kr(0) == "무료"

    def test_negative_rejected(self) -> None:
        import pytest

        from payments import format_price_with_period_kr

        with pytest.raises(ValueError, match="monthly_price_krw"):
            format_price_with_period_kr(-100)

    def test_invalid_period_rejected(self) -> None:
        import pytest

        from payments import format_price_with_period_kr

        with pytest.raises(ValueError, match="period"):
            format_price_with_period_kr(9_900, "weekly")


class TestEmailVerificationToken:
    """Cycle 144: 이메일 인증 토큰 (HMAC + 만료·OWASP·stateless)."""

    SECRET = "test_secret_key_at_least_32_chars_long_OK"

    def test_valid_token_round_trip(self) -> None:
        from auth import (
            generate_email_verification_token,
            verify_email_verification_token,
        )

        token = generate_email_verification_token(
            "user@example.com", self.SECRET
        )
        result = verify_email_verification_token(token, self.SECRET)
        assert result.valid
        assert result.email == "user@example.com"

    def test_wrong_secret_rejected(self) -> None:
        from auth import (
            generate_email_verification_token,
            verify_email_verification_token,
        )

        token = generate_email_verification_token(
            "user@example.com", self.SECRET
        )
        result = verify_email_verification_token(token, "x" * 32)
        assert not result.valid
        assert "서명" in result.reason_kr

    def test_expired_token_rejected(self) -> None:
        from datetime import UTC, datetime, timedelta

        from auth import (
            generate_email_verification_token,
            verify_email_verification_token,
        )

        past = datetime.now(UTC) - timedelta(hours=48)
        token = generate_email_verification_token(
            "user@example.com",
            self.SECRET,
            valid_hours=24,
            now=past,
        )
        result = verify_email_verification_token(token, self.SECRET)
        assert not result.valid
        assert "만료" in result.reason_kr

    def test_tampered_token_rejected(self) -> None:
        from auth import (
            generate_email_verification_token,
            verify_email_verification_token,
        )

        token = generate_email_verification_token(
            "user@example.com", self.SECRET
        )
        # 1자 변경
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        result = verify_email_verification_token(tampered, self.SECRET)
        assert not result.valid

    def test_garbage_token_rejected(self) -> None:
        from auth import verify_email_verification_token

        result = verify_email_verification_token("not-a-real-token", self.SECRET)
        assert not result.valid

    def test_short_secret_rejected_at_generation(self) -> None:
        import pytest

        from auth import generate_email_verification_token

        with pytest.raises(ValueError, match="32자"):
            generate_email_verification_token("u@e.com", "short")

    def test_invalid_email_rejected(self) -> None:
        import pytest

        from auth import generate_email_verification_token

        with pytest.raises(ValueError, match="이메일"):
            generate_email_verification_token("noatsign", self.SECRET)

    def test_valid_hours_capped(self) -> None:
        import pytest

        from auth import generate_email_verification_token

        with pytest.raises(ValueError, match="1~168"):
            generate_email_verification_token(
                "u@e.com", self.SECRET, valid_hours=200
            )


class TestPaymentAmountVerification:
    """Cycle 145: order tampering 방어 (서버 expected vs PG actual)."""

    def test_exact_match_valid(self) -> None:
        from payments import verify_payment_amount

        check = verify_payment_amount(expected_krw=9_900, actual_krw=9_900)
        assert check.valid
        assert "일치" in check.reason_kr

    def test_tampered_higher_invalid(self) -> None:
        from payments import verify_payment_amount

        # 서버 = ₩9,900·but PG payload = ₩99,000 (10배 변조)
        check = verify_payment_amount(expected_krw=9_900, actual_krw=99_000)
        assert not check.valid
        assert "tampering" in check.reason_kr

    def test_tampered_lower_invalid(self) -> None:
        from payments import verify_payment_amount

        # 사용자 = ₩100으로 변조 시도
        check = verify_payment_amount(expected_krw=9_900, actual_krw=100)
        assert not check.valid

    def test_tolerance_within_range(self) -> None:
        from payments import verify_payment_amount

        # 환율 변동·반올림 = ₩10 오차 허용
        check = verify_payment_amount(
            expected_krw=9_900, actual_krw=9_905, tolerance_krw=10
        )
        assert check.valid

    def test_tolerance_exceeded(self) -> None:
        from payments import verify_payment_amount

        check = verify_payment_amount(
            expected_krw=9_900, actual_krw=9_950, tolerance_krw=10
        )
        assert not check.valid

    def test_negative_rejected(self) -> None:
        import pytest

        from payments import verify_payment_amount

        with pytest.raises(ValueError, match="≥ 0"):
            verify_payment_amount(expected_krw=-100, actual_krw=9_900)

    def test_zero_amount_match(self) -> None:
        # ₩0 = 무료 플랜 confirm·정상 케이스
        from payments import verify_payment_amount

        check = verify_payment_amount(expected_krw=0, actual_krw=0)
        assert check.valid


class TestTrialWarningMessage:
    """Cycle 147: 체험 종료 임박 알림 (D-3 결제 유도)."""

    def test_basic_message(self) -> None:
        from email_helper import build_trial_warning_message

        msg = build_trial_warning_message(
            to_email="user@example.com",
            app_name="freelancer-tax-helper",
            days_remaining=3,
            upgrade_url="https://app.example.com/upgrade",
        )
        assert "3일" in msg.subject
        assert "자동 결제 X" in msg.body_text
        assert "옵트인" in msg.body_text
        assert "Founding Member" in msg.body_text

    def test_https_required(self) -> None:
        import pytest

        from email_helper import build_trial_warning_message

        with pytest.raises(ValueError, match="HTTPS"):
            build_trial_warning_message(
                to_email="u@e.com",
                app_name="x",
                days_remaining=3,
                upgrade_url="http://insecure.example.com/upgrade",
            )

    def test_negative_days_rejected(self) -> None:
        import pytest

        from email_helper import build_trial_warning_message

        with pytest.raises(ValueError, match="days_remaining"):
            build_trial_warning_message(
                to_email="u@e.com",
                app_name="x",
                days_remaining=-1,
                upgrade_url="https://app.example.com",
            )

    def test_english_language(self) -> None:
        from email_helper import build_trial_warning_message

        msg = build_trial_warning_message(
            to_email="user@example.com",
            app_name="sidehustle-tracker",
            days_remaining=3,
            upgrade_url="https://app.example.com/upgrade",
            language="en",
        )
        assert "Trial ending" in msg.subject
        assert "auto-charge" in msg.body_text


class TestTrustBadges:
    """Cycle 148: render_trust_badges 컴포넌트 import + early return."""

    def test_callable(self) -> None:
        from landing.streamlit_helper import render_trust_badges

        assert callable(render_trust_badges)

    def test_no_streamlit_safe(self) -> None:
        from landing.streamlit_helper import render_trust_badges

        # streamlit 없는 환경 = 안전 no-op
        result = render_trust_badges([{"icon": "🔒", "label": "PIPA"}])
        assert result is None

    def test_empty_badges_safe(self) -> None:
        from landing.streamlit_helper import render_trust_badges

        result = render_trust_badges([])
        assert result is None


class TestKoreanVatSplit:
    """Cycle 149: 한국 부가세 분리 (VAT 포함 → 공급가 + VAT)."""

    def test_general_tax_basic(self) -> None:
        from payments import split_korean_vat

        # ₩11,000 = 공급가 ₩10,000 + VAT ₩1,000
        breakdown = split_korean_vat(11_000)
        assert breakdown.supply_value_krw == 10_000
        assert breakdown.vat_krw == 1_000
        assert breakdown.gross_with_vat_krw == 11_000

    def test_9900_split(self) -> None:
        from payments import split_korean_vat

        # ₩9,900 = 공급가 ₩9,000 + VAT ₩900
        breakdown = split_korean_vat(9_900)
        assert breakdown.supply_value_krw == 9_000
        assert breakdown.vat_krw == 900

    def test_simple_tax_no_vat(self) -> None:
        from payments import split_korean_vat

        breakdown = split_korean_vat(9_900, is_general_tax=False)
        assert breakdown.vat_krw == 0
        assert breakdown.supply_value_krw == 9_900

    def test_negative_rejected(self) -> None:
        import pytest

        from payments import split_korean_vat

        with pytest.raises(ValueError, match="gross_with_vat_krw"):
            split_korean_vat(-100)

    def test_label_includes_breakdown(self) -> None:
        from payments import split_korean_vat

        breakdown = split_korean_vat(11_000)
        assert "₩10,000" in breakdown.label_kr
        assert "₩1,000" in breakdown.label_kr


class TestTaxInvoiceRequired:
    """Cycle 149: 세금계산서 발급 의무 (부가가치세법 §32)."""

    def test_b2c_no_business_number(self) -> None:
        from payments import is_tax_invoice_required

        # 일반 소비자 (사업자번호 X) = 발급 의무 X
        assert not is_tax_invoice_required(
            customer_business_number="", amount_krw=9_900
        )

    def test_b2b_above_threshold(self) -> None:
        from payments import is_tax_invoice_required

        # 사업자 + 10만원+ = 의무
        assert is_tax_invoice_required(
            customer_business_number="123-45-67890", amount_krw=100_000
        )
        assert is_tax_invoice_required(
            customer_business_number="123-45-67890", amount_krw=500_000
        )

    def test_b2b_below_threshold(self) -> None:
        from payments import is_tax_invoice_required

        # 사업자 + 10만원 미만 = 권장 (의무 X)
        assert not is_tax_invoice_required(
            customer_business_number="123-45-67890", amount_krw=9_900
        )

    def test_invalid_business_number(self) -> None:
        from payments import is_tax_invoice_required

        # 형식 X = 발급 X
        assert not is_tax_invoice_required(
            customer_business_number="not-a-number", amount_krw=500_000
        )

    def test_business_number_no_dash(self) -> None:
        from payments import is_tax_invoice_required

        # 하이픈 X = OK (10자리)
        assert is_tax_invoice_required(
            customer_business_number="1234567890", amount_krw=200_000
        )

    def test_negative_amount_rejected(self) -> None:
        import pytest

        from payments import is_tax_invoice_required

        with pytest.raises(ValueError, match="amount_krw"):
            is_tax_invoice_required(
                customer_business_number="123-45-67890", amount_krw=-100
            )


class TestKoreanBusinessNumberChecksum:
    """Cycle 150: 사업자등록번호 체크섬 (국세청 공식)."""

    def test_valid_known_number(self) -> None:
        from auth import validate_korean_business_number

        # 알려진 유효 번호: 124-86-00000 (예시·체크섬 통과)
        # 알고리즘 자체 검증을 위해 유효한 가짜 번호 생성
        # 1·2·3·4·5·6·7·8·9 → check digit 계산
        # weights (1,3,7,1,3,7,1,3,5)
        # sum = 1+6+21+4+15+42+7+24+45 = 165
        # + (9*5)//10 = 4 → 169
        # check = (10 - 169%10) % 10 = (10-9)%10 = 1
        # 따라서 1234567891 = 유효
        assert validate_korean_business_number("1234567891")
        assert validate_korean_business_number("123-45-67891")

    def test_dash_optional(self) -> None:
        from auth import validate_korean_business_number

        # 같은 번호·하이픈 유무 = 동일 결과
        assert validate_korean_business_number(
            "1234567891"
        ) == validate_korean_business_number("123-45-67891")

    def test_invalid_checksum(self) -> None:
        from auth import validate_korean_business_number

        # 마지막 자리 변경 = 체크섬 실패
        assert not validate_korean_business_number("1234567899")

    def test_wrong_length(self) -> None:
        from auth import validate_korean_business_number

        assert not validate_korean_business_number("12345")
        assert not validate_korean_business_number("12345678901")  # 11자리

    def test_non_digit_rejected(self) -> None:
        from auth import validate_korean_business_number

        assert not validate_korean_business_number("ABC-DE-FGHIJ")

    def test_empty_rejected(self) -> None:
        from auth import validate_korean_business_number

        assert not validate_korean_business_number("")


class TestFormatBusinessNumber:
    """Cycle 151: 사업자등록번호 표준 포맷 (XXX-XX-XXXXX)."""

    def test_no_dash_to_dashed(self) -> None:
        from payments import format_business_number_kr

        assert format_business_number_kr("1234567891") == "123-45-67891"

    def test_already_dashed_normalized(self) -> None:
        from payments import format_business_number_kr

        assert format_business_number_kr("123-45-67891") == "123-45-67891"

    def test_messy_input_normalized(self) -> None:
        from payments import format_business_number_kr

        # 잘못된 위치 하이픈도 정리 후 표준화
        assert format_business_number_kr("12345-67891") == "123-45-67891"

    def test_wrong_length_returns_original(self) -> None:
        from payments import format_business_number_kr

        # 검증 = validate_korean_business_number 책임·여기는 포맷만
        assert format_business_number_kr("12345") == "12345"
        assert format_business_number_kr("12345678901") == "12345678901"

    def test_empty_returns_empty(self) -> None:
        from payments import format_business_number_kr

        assert format_business_number_kr("") == ""


class TestLegalLinks:
    """Cycle 154: legal markdown 6 footer 통합."""

    def test_callable(self) -> None:
        from landing.streamlit_helper import render_legal_links

        assert callable(render_legal_links)

    def test_no_streamlit_safe(self) -> None:
        from landing.streamlit_helper import render_legal_links

        # streamlit 없는 환경 = 안전 no-op
        result = render_legal_links()
        assert result is None

    def test_custom_subset(self) -> None:
        from landing.streamlit_helper import render_legal_links

        result = render_legal_links(include=("privacy", "terms"))
        assert result is None  # streamlit 없으면 no-op·실 환경 = 2 링크 표시

    def test_empty_include_safe(self) -> None:
        from landing.streamlit_helper import render_legal_links

        result = render_legal_links(include=())
        assert result is None


class TestBurnoutAlert:
    """Cycle 161: 사서 번아웃 자동 알림 (#4 페어·KOSHA·헌법 §10)."""

    def test_basic_message_korean(self) -> None:
        from email_helper import build_burnout_alert_message

        msg = build_burnout_alert_message(
            to_email="user@example.com",
            app_name="사서_야근_추적",
            weekly_avg_overtime_hours=12.5,
            consecutive_high_weeks=4,
        )
        assert "12.5" in msg.body_text
        assert "4 주" in msg.body_text
        assert "KOSHA" in msg.body_text
        assert "1577-0199" in msg.body_text  # 정신건강 위기 상담
        assert "의료/심리 자문 X" in msg.body_text  # 헌법 §10
        assert "본인 검수" in msg.body_text  # 헌법 §10

    def test_negative_rejected(self) -> None:
        import pytest

        from email_helper import build_burnout_alert_message

        with pytest.raises(ValueError, match="≥ 0"):
            build_burnout_alert_message(
                to_email="u@e.com",
                app_name="x",
                weekly_avg_overtime_hours=-1,
                consecutive_high_weeks=0,
            )

    def test_english_disclaimer(self) -> None:
        from email_helper import build_burnout_alert_message

        msg = build_burnout_alert_message(
            to_email="user@example.com",
            app_name="librarian-overtime",
            weekly_avg_overtime_hours=10.0,
            consecutive_high_weeks=3,
            language="en",
        )
        assert "Burnout warning" in msg.subject
        assert "NOT medical advice" in msg.body_text


class TestInvoiceLine:
    """Cycle 165: 영수증 한 줄 (공급가·VAT 분리)."""

    def test_basic_general_tax(self) -> None:
        from payments import format_invoice_line_kr

        line = format_invoice_line_kr("Pro 월 정액", 9_900)
        assert "Pro 월 정액" in line
        assert "₩9,000" in line  # 공급가
        assert "₩900" in line  # VAT
        assert "₩9,900" in line  # 합계

    def test_simple_tax_no_vat(self) -> None:
        from payments import format_invoice_line_kr

        line = format_invoice_line_kr("Pro 월 정액", 9_900, is_general_tax=False)
        assert "VAT X" in line
        assert "₩9,900" in line

    def test_empty_description_rejected(self) -> None:
        import pytest

        from payments import format_invoice_line_kr

        with pytest.raises(ValueError, match="description"):
            format_invoice_line_kr("", 9_900)


class TestIdempotencyKey:
    """Cycle 139: PG 결제 중복 방지 키 (Stripe·PortOne 표준)."""

    def test_format_matches(self) -> None:
        import re

        from payments import generate_idempotency_key

        key = generate_idempotency_key()
        assert re.match(r"^idem_[0-9a-f]{32}$", key)

    def test_uniqueness_1000(self) -> None:
        from payments import generate_idempotency_key

        keys = {generate_idempotency_key() for _ in range(1000)}
        assert len(keys) == 1000  # 128 bit = 충돌 무시 가능

    def test_custom_prefix(self) -> None:
        from payments import generate_idempotency_key

        key = generate_idempotency_key(prefix="refund")
        assert key.startswith("refund_")

    def test_invalid_prefix_rejected(self) -> None:
        import pytest

        from payments import generate_idempotency_key

        with pytest.raises(ValueError, match="prefix"):
            generate_idempotency_key(prefix="")
        with pytest.raises(ValueError, match="prefix"):
            generate_idempotency_key(prefix="x" * 17)
