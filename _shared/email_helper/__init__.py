"""30-apps 공유 이메일 wrapper template (Resend 기반).

ADR 0058 정합·헌법 §3 (API 키 .env)·전자상거래법 의무 (영수증·환불 7일).

벤치마크: Resend (외부 research·월 100통 무료·이후 $20/월)·React Email 템플릿.

원칙:
- 이메일 = 결제 기록 + 환영 + 갱신 + 환불·기타 X (스팸 회피)
- 한국어 + 영어 2 템플릿
- 한국 정합: 전자상거래법 §13 (영수증)·§17 (환불 7일)·신용정보법 (mailing list)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum


class EmailType(StrEnum):
    """필수 이메일 종류 (스팸 회피)."""

    WELCOME = "welcome"  # 가입 환영·activation
    RECEIPT = "receipt"  # 결제 영수증 (전자상거래법 §13)
    RENEWAL_NOTICE = "renewal_notice"  # 14일 전 갱신 알림
    CANCEL = "cancel"  # 취소·환불 확인
    PASSWORD_RESET = "password_reset"  # 비밀번호 재설정


@dataclass(frozen=True)
class EmailConfig:
    """Resend 설정 (env from .env)."""

    api_key: str
    from_email: str  # noreply@<your-domain>
    from_name: str  # "30-apps Team" 또는 앱별
    reply_to: str = ""
    sandbox: bool = True

    @classmethod
    def from_env(cls) -> EmailConfig:
        return cls(
            api_key=os.environ.get("RESEND_API_KEY", ""),
            from_email=os.environ.get("EMAIL_FROM", ""),
            from_name=os.environ.get("EMAIL_FROM_NAME", "30-apps"),
            reply_to=os.environ.get("EMAIL_REPLY_TO", ""),
            sandbox=os.environ.get("RESEND_SANDBOX", "true").lower() == "true",
        )

    def is_configured(self) -> bool:
        return bool(self.api_key) and bool(self.from_email)


@dataclass(frozen=True)
class EmailMessage:
    """이메일 메시지 (Resend send 호환)."""

    to_email: str
    type: str  # EmailType.value
    subject: str
    body_html: str
    body_text: str  # 텍스트 버전 (스팸 회피·접근성)
    language: str = "ko"  # ko·en
    reply_to: str = ""


def build_welcome_message(
    to_email: str, app_name: str, language: str = "ko"
) -> EmailMessage:
    """환영 메일 template (한국어/영어)."""
    if language == "ko":
        subject = f"[{app_name}] 가입을 환영합니다 🎉"
        body_text = (
            f"안녕하세요,\n\n"
            f"{app_name} 가입을 환영합니다.\n\n"
            f"본 서비스 = 자기 측정 보조이며 의료·법률·세무 자문 X 입니다.\n"
            f"개인정보 = 사용자 컴퓨터에서 처리되며 외부 서버 저장 X (헌법 §14).\n\n"
            f"문의: 답장 또는 처리방침 페이지\n"
            f"7일 내 환불 가능 (전자상거래법 §17)\n\n"
            f"감사합니다.\n{app_name} 팀"
        )
    else:
        subject = f"[{app_name}] Welcome aboard 🎉"
        body_text = (
            f"Hello,\n\n"
            f"Welcome to {app_name}.\n\n"
            f"This service = self-measurement assistance·NOT medical/legal/tax advice.\n"
            f"Data = local·no external server storage (privacy by design).\n\n"
            f"Contact: reply or privacy policy page\n"
            f"7-day refund (Korean Electronic Commerce Act §17)\n\n"
            f"Thank you.\n{app_name} Team"
        )

    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.WELCOME.value,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language=language,
    )


def build_receipt_message(
    to_email: str,
    app_name: str,
    amount_krw: int,
    transaction_id: str,
    language: str = "ko",
) -> EmailMessage:
    """결제 영수증 (전자상거래법 §13 의무)."""
    if language == "ko":
        subject = f"[{app_name}] 결제 영수증 #{transaction_id}"
        body_text = (
            f"결제가 완료되었습니다.\n\n"
            f"앱: {app_name}\n"
            f"금액: ₩{amount_krw:,}\n"
            f"거래번호: {transaction_id}\n\n"
            f"7일 내 환불 가능 (전자상거래법 §17)·문의 = 답장\n"
            f"세금계산서 = 별도 요청 시 발급 (PortOne·일반과세자)"
        )
    else:
        subject = f"[{app_name}] Payment receipt #{transaction_id}"
        body_text = (
            f"Payment completed.\n\n"
            f"App: {app_name}\n"
            f"Amount: ₩{amount_krw:,}\n"
            f"Transaction: {transaction_id}\n\n"
            f"7-day refund available."
        )

    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.RECEIPT.value,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language=language,
    )


def build_burnout_alert_message(
    to_email: str,
    app_name: str,
    weekly_avg_overtime_hours: float,
    consecutive_high_weeks: int,
    language: str = "ko",
) -> EmailMessage:
    """번아웃 위험 자동 알림 (#4 사서_야근_추적 페어·KOSHA 정합).

    Cycle 124 librarian_overtime.judge_burnout_risk = 높음/매우 높음 시 발송.
    헌법 §10 정합: 의료 자문 X·자기 측정 보조·사용자 검수 의무 명시.
    """
    if weekly_avg_overtime_hours < 0 or consecutive_high_weeks < 0:
        msg = "수치 ≥ 0 의무"
        raise ValueError(msg)
    if language == "ko":
        subject = (
            f"[{app_name}] 번아웃 위험 신호·"
            f"주 평균 야근 {weekly_avg_overtime_hours}h"
        )
        body_text = (
            f"안녕하세요,\n\n"
            f"{app_name} 분석 결과·번아웃 사전 신호가 감지되었습니다.\n\n"
            f"📊 측정값:\n"
            f"- 주 평균 야근: {weekly_avg_overtime_hours} 시간\n"
            f"- 연속 고부담 주: {consecutive_high_weeks} 주\n\n"
            f"권고 (KOSHA 정합):\n"
            f"- 즉시 휴가 검토·면담 권고\n"
            f"- 1주 야근 ≤ 12시간 목표 (근로기준법 §53)\n"
            f"- 충분한 수면 (성인 7~9시간)\n\n"
            f"⚠ 면책: 본 알림 = 자기 측정 보조·**의료/심리 자문 X**.\n"
            f"   증상 지속 시 = 정신건강 전문의 상담 권고 (1577-0199 24h).\n\n"
            f"본인 검수 후 결정 (헌법 §10 정합).\n\n"
            f"{app_name} 팀"
        )
    else:
        subject = (
            f"[{app_name}] Burnout warning signal · "
            f"weekly overtime avg {weekly_avg_overtime_hours}h"
        )
        body_text = (
            f"Hello,\n\n"
            f"{app_name} detected early burnout signals.\n\n"
            f"Metrics:\n"
            f"- Weekly overtime avg: {weekly_avg_overtime_hours} hours\n"
            f"- Consecutive high-load weeks: {consecutive_high_weeks}\n\n"
            f"Recommendations (KOSHA-aligned):\n"
            f"- Consider time off and consultation\n"
            f"- Target ≤ 12h overtime/week\n"
            f"- 7-9 hours of sleep\n\n"
            f"Disclaimer: self-measurement aid only · NOT medical advice.\n"
            f"If symptoms persist, consult a mental health professional.\n\n"
            f"{app_name} Team"
        )

    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.RENEWAL_NOTICE.value,  # 운영 알림 메시지로 분류
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language=language,
    )


def build_trial_warning_message(
    to_email: str,
    app_name: str,
    days_remaining: int,
    upgrade_url: str,
    language: str = "ko",
) -> EmailMessage:
    """체험 종료 임박 알림 (D-3·결제 유도·외부 901 진단 정합).

    Cycle 124 calculate_trial_status·is_warning=True 시 발송.
    핵심 = "체험 종료 후 자동 결제 X" 명시 (PIPA·전자상거래법 옵트인).
    """
    if days_remaining < 0:
        msg = "days_remaining ≥ 0 의무"
        raise ValueError(msg)
    if not upgrade_url.startswith("https://"):
        msg = "upgrade_url = HTTPS 의무 (보안)"
        raise ValueError(msg)
    if language == "ko":
        subject = f"[{app_name}] 체험 {days_remaining}일 남음·결제 시 계속 사용"
        body_text = (
            f"안녕하세요,\n\n"
            f"{app_name} 14일 무료 체험이 {days_remaining}일 남았습니다.\n\n"
            f"체험 종료 시:\n"
            f"- ❌ 자동 결제 X (옵트인 의무)\n"
            f"- ✅ 결제 시 계속 사용 가능\n"
            f"- ✅ Founding Member 영구 50% 할인 (선착순)\n\n"
            f"결제 → {upgrade_url}\n\n"
            f"그동안의 데이터 = 사용자 컴퓨터 보존 (헌법 §14).\n"
            f"미결제 시 = 자동 정리·복구 가능 (30일 보관).\n\n"
            f"감사합니다.\n{app_name} 팀"
        )
    else:
        subject = f"[{app_name}] Trial ending in {days_remaining} days"
        body_text = (
            f"Hello,\n\n"
            f"Your {app_name} free trial ends in {days_remaining} days.\n\n"
            f"After trial:\n"
            f"- No auto-charge (opt-in required)\n"
            f"- Pay to continue\n"
            f"- Founding Member 50% off (limited)\n\n"
            f"Upgrade: {upgrade_url}\n\n"
            f"Your data = local·preserved 30 days.\n\n"
            f"{app_name} Team"
        )
    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.RENEWAL_NOTICE.value,  # 알림 종류 = 운영 메시지
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language=language,
    )


def build_renewal_notice_message(
    to_email: str,
    app_name: str,
    next_charge_krw: int,
    next_charge_date: str,  # ISO 8601: 2026-06-23
    language: str = "ko",
) -> EmailMessage:
    """14일 전 갱신 알림 (전자상거래법 §17 정합·해지 권리 안내).

    PO 영구 명령 정합: 자동 결제 = 사용자 사전 인지 의무·"몰래 자동결제" X.
    """
    if next_charge_krw < 0:
        msg = "next_charge_krw ≥ 0 의무"
        raise ValueError(msg)
    if language == "ko":
        subject = f"[{app_name}] {next_charge_date} 갱신 예정 ₩{next_charge_krw:,}"
        body_text = (
            f"안녕하세요,\n\n"
            f"{app_name} 자동 갱신 14일 전 안내드립니다.\n\n"
            f"갱신일: {next_charge_date}\n"
            f"청구 금액: ₩{next_charge_krw:,}\n\n"
            f"해지 = 갱신일 전 마이페이지에서 클릭 1회 (즉시 처리)\n"
            f"환불 = 결제 후 7일 내 (전자상거래법 §17)\n\n"
            f"감사합니다.\n{app_name} 팀"
        )
    else:
        subject = f"[{app_name}] Renewal in 14 days: ₩{next_charge_krw:,} on {next_charge_date}"
        body_text = (
            f"Hello,\n\n"
            f"{app_name} auto-renewal notice (14 days advance).\n\n"
            f"Renewal date: {next_charge_date}\n"
            f"Amount: ₩{next_charge_krw:,}\n\n"
            f"Cancel = one-click from My Page before renewal date.\n"
            f"7-day refund window after charge.\n\n"
            f"Thanks,\n{app_name} Team"
        )

    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.RENEWAL_NOTICE.value,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language=language,
    )


def build_weekly_kpi_message(
    to_email: str,
    app_name: str,
    funnel_label_kr: str,  # ConversionFunnel.label_kr() 결과
    diagnosis_kr: str,  # diagnose_funnel() 결과
    week_label: str,  # 예: "2026-W19" 또는 "2026-05-04~10"
) -> EmailMessage:
    """주간 운영 KPI 알림 (PO·1인 운영 자동화·외부 발사 후 매주 자동).

    Cycle 140 ConversionFunnel + Cycle 142 본 함수 연결.
    Resend cron 또는 GitHub Actions weekly trigger 활용 권장.
    """
    if not funnel_label_kr or not diagnosis_kr or not week_label:
        msg = "funnel_label·diagnosis·week_label 모두 비어있을 수 없음"
        raise ValueError(msg)
    subject = f"[{app_name}] 주간 KPI {week_label}"
    body_text = (
        f"안녕하세요 PO,\n\n"
        f"{app_name} {week_label} 주간 운영 KPI 자동 알림.\n\n"
        f"📊 funnel:\n{funnel_label_kr}\n\n"
        f"🔍 진단:\n{diagnosis_kr}\n\n"
        f"근거: 외부 901 진단 + Habit Pixel 벤치마크 (구독 SaaS 구조).\n"
        f"다음 cycle = 진단 영역 자동 보강 또는 PO 결정.\n\n"
        f"{app_name} 자동 운영"
    )
    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.RENEWAL_NOTICE.value,  # 운영 메시지 = 재사용
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language="ko",
    )


def build_password_reset_message(
    to_email: str,
    app_name: str,
    reset_url: str,
    expires_in_minutes: int = 30,
    language: str = "ko",
) -> EmailMessage:
    """비밀번호 재설정 이메일 (15~60분 만료·OWASP 권장).

    보안: reset_url = 1회용 토큰·HTTPS 의무·만료 30분 기본.
    """
    if expires_in_minutes <= 0 or expires_in_minutes > 60:
        msg = "expires_in_minutes = 1~60 의무 (OWASP 권장)"
        raise ValueError(msg)
    if not reset_url.startswith("https://"):
        msg = "reset_url = HTTPS 의무 (보안)"
        raise ValueError(msg)
    if language == "ko":
        subject = f"[{app_name}] 비밀번호 재설정 (만료 {expires_in_minutes}분)"
        body_text = (
            f"비밀번호 재설정을 요청하셨습니다.\n\n"
            f"아래 링크 클릭 → 새 비밀번호 설정:\n"
            f"{reset_url}\n\n"
            f"만료: {expires_in_minutes}분\n"
            f"본인이 요청하지 않았다면 = 무시하세요·계정 안전합니다.\n\n"
            f"{app_name} 팀"
        )
    else:
        subject = f"[{app_name}] Password reset (expires in {expires_in_minutes} min)"
        body_text = (
            f"You requested a password reset.\n\n"
            f"Click below to set a new password:\n"
            f"{reset_url}\n\n"
            f"Expires in {expires_in_minutes} minutes.\n"
            f"If you didn't request this, ignore — your account is safe.\n\n"
            f"{app_name} Team"
        )

    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.PASSWORD_RESET.value,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language=language,
    )


def build_cancel_message(
    to_email: str,
    app_name: str,
    refund_amount_krw: int = 0,
    language: str = "ko",
) -> EmailMessage:
    """취소·환불 확인 (전자상거래법 §17·환불 7일 내 처리 의무)."""
    if refund_amount_krw < 0:
        msg = "refund_amount_krw ≥ 0 의무"
        raise ValueError(msg)
    if language == "ko":
        subject = f"[{app_name}] 해지 확인 (환불 ₩{refund_amount_krw:,})"
        body_text = (
            f"해지가 완료되었습니다.\n\n"
            f"앱: {app_name}\n"
            f"환불 금액: ₩{refund_amount_krw:,}\n"
            f"환불 처리: 카드사 영업일 3~5일 (PortOne 자동)\n\n"
            f"불편한 점이 있으셨다면 답장으로 알려주세요·개선에 반영합니다.\n\n"
            f"{app_name} 팀"
        )
    else:
        subject = f"[{app_name}] Cancellation confirmed (refund ₩{refund_amount_krw:,})"
        body_text = (
            f"Your cancellation is confirmed.\n\n"
            f"App: {app_name}\n"
            f"Refund: ₩{refund_amount_krw:,}\n"
            f"Refund processing: 3~5 business days (PortOne auto)\n\n"
            f"Please reply with any feedback — it goes directly to the founder.\n\n"
            f"{app_name} Team"
        )

    body_html = body_text.replace("\n", "<br>")
    return EmailMessage(
        to_email=to_email,
        type=EmailType.CANCEL.value,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        language=language,
    )


__all__ = [
    "EmailConfig",
    "EmailMessage",
    "EmailType",
    "build_burnout_alert_message",
    "build_cancel_message",
    "build_password_reset_message",
    "build_receipt_message",
    "build_renewal_notice_message",
    "build_trial_warning_message",
    "build_weekly_kpi_message",
    "build_welcome_message",
]
