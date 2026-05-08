"""30-apps 공유 인증 wrapper template (Better Auth 기반).

ADR 0058 정합·캐시카우 통과 앱 = 즉시 활성·외부 가입 = PO 결정 시.
헌법 §3 (API 키 .env)·§14 (사용자 데이터 X)·PIPA 정합.

벤치마크: supastarter (2025~26 NextAuth → Better Auth 전환)·외부 research.

원칙:
- 이메일 + 비밀번호 (소셜 X = 락인 회피)
- bcrypt 해시 (헌법 §3·PIPA 정합)
- TLS 1.2+ (PG 자동)
- 옵트인 동의 (PIPA·전자상거래법)
- 사용자 데이터 = 사용자 컴퓨터 + 결제 기록만 서버 (5년 의무)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class SignupRequest:
    """가입 요청 (헌법 §3 + PIPA 정합)."""

    email: str
    password_hash: str  # bcrypt 해시 (생성 = 호출자 책임·평문 X)
    consent_privacy: bool  # 처리방침 동의 (PIPA 의무)
    consent_terms: bool  # 이용약관 동의 (전자상거래법)
    consent_marketing: bool = False  # 옵트인 (선택)
    referral_code: str = ""

    def __post_init__(self) -> None:
        if not self.email or "@" not in self.email:
            raise ValueError("email은 유효해야 합니다")
        if not self.password_hash or len(self.password_hash) < 20:
            raise ValueError("password_hash는 bcrypt 해시여야 합니다 (평문 X)")
        if not self.consent_privacy:
            raise ValueError("처리방침 동의 필수 (PIPA)")
        if not self.consent_terms:
            raise ValueError("이용약관 동의 필수 (전자상거래법)")


@dataclass(frozen=True)
class AuthSession:
    """인증 세션·session_state 한정 (헌법 §14·refresh = 휘발)."""

    user_id: str
    email: str
    expires_at: str  # ISO 8601
    csrf_token: str = field(default_factory=lambda: secrets.token_urlsafe(32))


@dataclass(frozen=True)
class AuthConfig:
    """인증 설정 (env from .env)."""

    secret_key: str
    session_duration_hours: int = 24 * 14  # 2주 (전자상거래법 환불 정합)
    bcrypt_rounds: int = 12  # OWASP 권장 (2026)
    sandbox: bool = True

    @classmethod
    def from_env(cls) -> AuthConfig:
        """env에서 로드 (헌법 §3 정합)."""
        return cls(
            secret_key=os.environ.get("AUTH_SECRET_KEY", ""),
            sandbox=os.environ.get("AUTH_SANDBOX", "true").lower() == "true",
        )

    def is_configured(self) -> bool:
        return bool(self.secret_key) and len(self.secret_key) >= 32


def generate_csrf_token() -> str:
    """CSRF 토큰 (secrets.token_urlsafe·128 bit)."""
    return secrets.token_urlsafe(32)


def is_session_expired(session: AuthSession) -> bool:
    """세션 만료 확인 (UTC ISO 8601 기준)."""
    try:
        expires = datetime.fromisoformat(session.expires_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    return datetime.now(UTC) >= expires


# 가입 동의 항목 (PIPA·전자상거래법 정합)
REQUIRED_CONSENTS: dict[str, str] = {
    "privacy": "개인정보처리방침 동의 (PIPA 의무)",
    "terms": "이용약관 동의 (전자상거래법 의무)",
}

OPTIONAL_CONSENTS: dict[str, str] = {
    "marketing": "마케팅 정보 수신 (옵트인·선택)",
}


# 비밀번호 정책 (OWASP 2026·NIST SP 800-63B 정합)
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 64  # bcrypt 72 byte 한계 - 여유


@dataclass(frozen=True)
class PasswordCheck:
    """비밀번호 강도 검증 결과."""

    is_valid: bool
    score: int  # 0~4 (NIST 분류)
    issues_kr: tuple[str, ...]
    label_kr: str  # 약함·보통·강함·매우 강함


def validate_password_strength(password: str) -> PasswordCheck:
    """OWASP·NIST 정합 비밀번호 검증.

    8~64자·문자 다양성 가산·연속·반복 차감 (간단 휴리스틱).
    실 운영 = zxcvbn 또는 HIBP API 추가 권장.
    """
    issues: list[str] = []
    if len(password) < MIN_PASSWORD_LENGTH:
        issues.append(f"최소 {MIN_PASSWORD_LENGTH}자 의무")
    if len(password) > MAX_PASSWORD_LENGTH:
        issues.append(f"최대 {MAX_PASSWORD_LENGTH}자 (bcrypt 72byte 한계)")

    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(not c.isalnum() for c in password)
    diversity = sum([has_lower, has_upper, has_digit, has_symbol])

    if diversity < 2:
        issues.append("문자 종류 2+ 의무 (영문·숫자·기호)")

    weak_patterns = ("12345", "password", "qwerty", "abcdef", "111111")
    pwd_lower = password.lower()
    for pattern in weak_patterns:
        if pattern in pwd_lower:
            issues.append(f"흔한 패턴 차단: '{pattern}'")
            break

    is_valid = not issues
    if not is_valid:
        score = 0
        label = "사용 불가"
    elif len(password) >= 16 and diversity >= 3:
        score = 4
        label = "매우 강함"
    elif len(password) >= 12 and diversity >= 3:
        score = 3
        label = "강함"
    elif len(password) >= 10 and diversity >= 2:
        score = 2
        label = "보통"
    else:
        score = 1
        label = "약함"

    return PasswordCheck(
        is_valid=is_valid,
        score=score,
        issues_kr=tuple(issues),
        label_kr=label,
    )


DEFAULT_EMAIL_TOKEN_HOURS = 24  # 이메일 인증 만료 (OWASP 권장 ≤ 24h)


def generate_email_verification_token(
    email: str,
    secret_key: str,
    valid_hours: int = DEFAULT_EMAIL_TOKEN_HOURS,
    now: datetime | None = None,
) -> str:
    """이메일 인증 토큰 생성 (HMAC SHA-256 + 만료·서버 상태 X·stateless).

    형식: base64url(email|expiry_iso|hmac_hex)
    검증 = verify_email_verification_token() = HMAC 재계산·만료 확인.

    Args:
        email: 인증 대상 이메일
        secret_key: 앱 비밀 키 (.env·헌법 §3·≥ 32자)
        valid_hours: 만료 (기본 24h·최대 168h = 1주)
        now: 테스트용

    Returns:
        URL-safe 토큰·이메일 클릭 1회용
    """
    if not email or "@" not in email:
        msg = "유효한 이메일 의무"
        raise ValueError(msg)
    if not secret_key or len(secret_key) < 32:
        msg = "secret_key ≥ 32자 의무 (헌법 §3)"
        raise ValueError(msg)
    if not 1 <= valid_hours <= 168:
        msg = "valid_hours = 1~168 의무 (OWASP)"
        raise ValueError(msg)
    current = now or datetime.now(UTC)
    expiry = current + timedelta(hours=valid_hours)
    expiry_iso = expiry.isoformat()
    material = f"{email}|{expiry_iso}".encode("utf-8")
    sig = hmac.new(secret_key.encode("utf-8"), material, hashlib.sha256).hexdigest()
    payload = f"{email}|{expiry_iso}|{sig}".encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


@dataclass(frozen=True)
class EmailTokenResult:
    """이메일 인증 검증 결과."""

    valid: bool
    email: str  # valid 시만 신뢰
    reason_kr: str


def verify_email_verification_token(
    token: str,
    secret_key: str,
    now: datetime | None = None,
) -> EmailTokenResult:
    """이메일 인증 토큰 검증 (timing-safe·만료·서명·이메일 추출)."""
    if not token or not secret_key:
        return EmailTokenResult(False, "", "토큰 또는 secret_key 누락")
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return EmailTokenResult(False, "", "토큰 형식 오류")
    parts = decoded.split("|")
    if len(parts) != 3:
        return EmailTokenResult(False, "", "토큰 구조 오류")
    email, expiry_iso, sig = parts
    # 서명 재계산
    material = f"{email}|{expiry_iso}".encode("utf-8")
    expected = hmac.new(
        secret_key.encode("utf-8"), material, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return EmailTokenResult(False, "", "서명 불일치 (위조 또는 변조)")
    # 만료 확인
    try:
        expiry = datetime.fromisoformat(expiry_iso)
    except ValueError:
        return EmailTokenResult(False, "", "만료 시점 형식 오류")
    current = now or datetime.now(UTC)
    if current >= expiry:
        return EmailTokenResult(False, "", "토큰 만료")
    return EmailTokenResult(True, email, "유효")


def validate_korean_business_number(number: str) -> bool:
    """한국 사업자등록번호 체크섬 검증 (국세청 공식 알고리즘).

    형식: XXX-XX-XXXXX (10자리·하이픈 옵션)
    체크섬: 가중치 (1·3·7·1·3·7·1·3·5)·9번째 자리 × 5의 십의자리 가산.
    마지막 1자리 = (10 - sum % 10) % 10

    근거: 국세청 「사업자등록번호 검증 규칙」.
    """
    if not number:
        return False
    cleaned = number.replace("-", "").strip()
    if len(cleaned) != 10 or not cleaned.isdigit():
        return False
    weights = (1, 3, 7, 1, 3, 7, 1, 3, 5)
    total = sum(int(cleaned[i]) * weights[i] for i in range(9))
    # 9번째 자리 × 5의 십의자리 가산
    total += (int(cleaned[8]) * 5) // 10
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(cleaned[9])


def redact_pii_for_log(text: str) -> str:
    """로그·디버그 출력 PII 마스킹 (PIPA 정합·KISA 권장).

    검출·치환:
    - 이메일 → mask_email_for_display 정합 (u***@example.com)
    - 한국 휴대폰 010-XXXX-XXXX → 010-****-XXXX
    - 사업자등록번호 XXX-XX-XXXXX → XXX-**-*****
    - 카드번호 (16자리 연속 숫자) → ****-****-****-XXXX
    """
    if not text:
        return text
    import re

    # 이메일
    def _mask_email_match(m: re.Match[str]) -> str:
        return mask_email_for_display(m.group(0))

    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        _mask_email_match,
        text,
    )
    # 한국 휴대폰
    text = re.sub(
        r"\b(01[0-9])-?(\d{3,4})-?(\d{4})\b",
        lambda m: f"{m.group(1)}-****-{m.group(3)}",
        text,
    )
    # 사업자등록번호 XXX-XX-XXXXX
    text = re.sub(
        r"\b(\d{3})-(\d{2})-(\d{5})\b",
        r"\1-**-*****",
        text,
    )
    # 카드번호 (16자리·하이픈 또는 공백)
    text = re.sub(
        r"\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b",
        r"****-****-****-\4",
        text,
    )
    return text


def mask_email_for_display(email: str) -> str:
    """이메일 마스킹 (PIPA 정합 화면 표시·CS 통화·로그).

    예:
        user@example.com → u***@example.com
        ab@x.kr → a*@x.kr
        a@x.kr → *@x.kr (1자 = 전부 마스킹)

    PIPA 정합: 화면·로그·고객센터 표시 시 의무 (전체 노출 차단).
    """
    if not validate_email_format(email):
        return "***"
    local, domain = email.split("@")
    if len(local) <= 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + "*" * (len(local) - 1)
    return f"{masked_local}@{domain}"


def validate_email_format(email: str) -> bool:
    """RFC 5321 간이 검증 (본격 검증 = 호출자·confirmation 이메일 발송).

    - @ 1개·local·domain 길이 1+·도메인에 . 포함·전체 254 이하
    """
    if not email or len(email) > 254:
        return False
    if email.count("@") != 1:
        return False
    local, domain = email.split("@")
    if not local or not domain:
        return False
    if "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith("."):
        return False
    return True


# 로그인 brute force 방어 (OWASP·PIPA 5대 패턴·KISA 권장)
DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_WINDOW_MINUTES = 5
DEFAULT_LOCKOUT_MINUTES = 15


class LoginRateLimiter:
    """로그인 시도 제한 (인메모리·OWASP brute force 방어).

    정책: 5분 창 내 5회 실패 → 15분 락아웃.
    실 운영 = Redis·DB로 영속화 권장 (인스턴스 1+ 시).
    """

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        window_minutes: int = DEFAULT_WINDOW_MINUTES,
        lockout_minutes: int = DEFAULT_LOCKOUT_MINUTES,
    ) -> None:
        if max_attempts <= 0 or window_minutes <= 0 or lockout_minutes <= 0:
            msg = "max_attempts·window_minutes·lockout_minutes > 0 의무"
            raise ValueError(msg)
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
        self.lockout = timedelta(minutes=lockout_minutes)
        self._attempts: dict[str, deque[datetime]] = {}
        self._locked_until: dict[str, datetime] = {}

    def is_locked(self, key: str, now: datetime | None = None) -> bool:
        """현재 락아웃 상태 여부 (key = 이메일·IP·해시 등)."""
        current = now or datetime.now(UTC)
        until = self._locked_until.get(key)
        if until is None:
            return False
        if current >= until:
            self._locked_until.pop(key, None)
            self._attempts.pop(key, None)
            return False
        return True

    def record_failure(self, key: str, now: datetime | None = None) -> bool:
        """실패 기록·락 발동 시 True 반환."""
        current = now or datetime.now(UTC)
        if self.is_locked(key, now=current):
            return True
        attempts = self._attempts.setdefault(key, deque())
        attempts.append(current)
        # 창 밖 시도 제거
        cutoff = current - self.window
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= self.max_attempts:
            self._locked_until[key] = current + self.lockout
            return True
        return False

    def record_success(self, key: str) -> None:
        """성공 시 카운터 초기화 (락 X 상태 한정)."""
        self._attempts.pop(key, None)
        self._locked_until.pop(key, None)

    def remaining_attempts(self, key: str, now: datetime | None = None) -> int:
        """남은 시도 횟수 (락 시 0)."""
        current = now or datetime.now(UTC)
        if self.is_locked(key, now=current):
            return 0
        attempts = self._attempts.get(key, deque())
        cutoff = current - self.window
        recent = sum(1 for t in attempts if t >= cutoff)
        return max(0, self.max_attempts - recent)


# Audit log 체인 (PIPA 5대 패턴 5/5·5만명+ 처리·민감정보 처리 의무)
GENESIS_HASH = "0" * 64  # 해시 체인 시작 (creation block 미존재 표식)


@dataclass(frozen=True)
class AuditEntry:
    """단일 audit 항목 (해시 체인 노드)."""

    timestamp: str  # ISO 8601 UTC
    event: str  # 예: "login", "signup", "refund", "consent_change"
    actor: str  # 사용자 ID·이메일 마스킹 (mask_email_for_display)
    payload_summary: str  # 요약 (전체 payload X·민감정보 직접 X)
    prev_hash: str
    hash: str

    def compute_hash(self) -> str:
        """본 entry의 해시 재계산 (검증용)."""
        material = (
            f"{self.timestamp}|{self.event}|{self.actor}|"
            f"{self.payload_summary}|{self.prev_hash}"
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()


class AuditChain:
    """인메모리 audit log 해시 체인 (PIPA·KISA 권장 정합).

    실 운영 = DB·파일·OpenSearch 영속화 + 본 클래스를 wrapping 권장.
    체인 무결성 = verify_chain() 호출·1 entry 변조 시 즉시 검출.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def append(
        self,
        event: str,
        actor: str,
        payload_summary: str = "",
        now: datetime | None = None,
    ) -> AuditEntry:
        """새 audit entry 추가·자동 해시 계산."""
        if not event:
            msg = "event 비어있을 수 없음"
            raise ValueError(msg)
        current = now or datetime.now(UTC)
        timestamp = current.isoformat()
        prev_hash = self._entries[-1].hash if self._entries else GENESIS_HASH
        # 임시 entry로 해시 계산
        material = f"{timestamp}|{event}|{actor}|{payload_summary}|{prev_hash}"
        entry_hash = hashlib.sha256(material.encode("utf-8")).hexdigest()
        entry = AuditEntry(
            timestamp=timestamp,
            event=event,
            actor=actor,
            payload_summary=payload_summary,
            prev_hash=prev_hash,
            hash=entry_hash,
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """전체 체인 무결성 검증 (변조 시 False)."""
        prev = GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != prev:
                return False
            if entry.compute_hash() != entry.hash:
                return False
            prev = entry.hash
        return True

    def __len__(self) -> int:
        return len(self._entries)

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        """불변 view (직접 변조 방지)."""
        return tuple(self._entries)


__all__ = [
    "DEFAULT_EMAIL_TOKEN_HOURS",
    "DEFAULT_LOCKOUT_MINUTES",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_WINDOW_MINUTES",
    "GENESIS_HASH",
    "MAX_PASSWORD_LENGTH",
    "MIN_PASSWORD_LENGTH",
    "OPTIONAL_CONSENTS",
    "REQUIRED_CONSENTS",
    "AuditChain",
    "AuditEntry",
    "AuthConfig",
    "AuthSession",
    "EmailTokenResult",
    "LoginRateLimiter",
    "PasswordCheck",
    "SignupRequest",
    "generate_csrf_token",
    "generate_email_verification_token",
    "is_session_expired",
    "mask_email_for_display",
    "redact_pii_for_log",
    "validate_email_format",
    "validate_korean_business_number",
    "validate_password_strength",
    "verify_email_verification_token",
]
