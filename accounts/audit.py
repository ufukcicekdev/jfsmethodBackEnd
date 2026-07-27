"""Merkezi audit log helper."""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest


def _get_ip(request) -> str | None:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_ua(request) -> str:
    if not request:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:300]


def log_action(
    action: str,
    *,
    actor=None,
    target_user=None,
    request=None,
    status: str = "success",
    detail: dict | None = None,
) -> None:
    try:
        from accounts.models import AuditLog
        AuditLog.objects.create(
            action=action,
            actor=actor,
            target_user=target_user,
            status=status,
            detail=detail or {},
            ip_address=_get_ip(request),
            user_agent=_get_ua(request),
        )
    except Exception:
        pass  # log hatası asla ana akışı bozmasın
