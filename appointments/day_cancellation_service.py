import logging
import threading
from collections import defaultdict

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Appointment, AppointmentStatus, ClinicHoliday, DayCancellation

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = [AppointmentStatus.PENDING, AppointmentStatus.APPROVED]


def get_day_cancellation_preview(target_date):
    appointments = (
        Appointment.objects.filter(
            appointment_datetime__date=target_date,
            status__in=ACTIVE_STATUSES,
        )
        .select_related("patient", "doctor")
        .order_by("appointment_datetime")
    )

    patients = {}
    for appt in appointments:
        key = appt.patient_id
        if key not in patients:
            patients[key] = {
                "patient_id": appt.patient_id,
                "patient_name": appt.patient.get_full_name() or appt.patient.username,
                "appointment_count": 0,
            }
        patients[key]["appointment_count"] += 1

    return {
        "date": target_date.isoformat(),
        "appointment_count": appointments.count(),
        "patient_count": len(patients),
        "patients": list(patients.values()),
    }


def _send_day_cancellation_email(
    patient_id: int,
    target_date_iso: str,
    reason: str,
    appointment_details: list[dict],
):
    try:
        from django.contrib.auth.models import User

        patient = User.objects.get(pk=patient_id)
        if not patient.email:
            logger.warning(
                "Cannot send day cancellation email: patient %s has no email",
                patient.username,
            )
            return False

        from datetime import date as date_cls

        target_date = date_cls.fromisoformat(target_date_iso)
        date_label = target_date.strftime("%d.%m.%Y")

        lines = []
        for item in appointment_details:
            lines.append(
                f"  • {item['time']} — Dr. {item['doctor_name']}"
            )
        appointments_text = "\n".join(lines)

        subject = f"FizyoTech — {date_label} Tarihli Dersiniz İptal Edildi"
        message = (
            f"Sayın {patient.get_full_name() or patient.username},\n\n"
            f"{date_label} tarihinde planlanmış ders/randevunuz iptal edilmiştir.\n\n"
            f"İptal edilen randevularınız:\n{appointments_text}\n\n"
            f"Mazaret / Açıklama:\n{reason}\n\n"
            f"Yeni randevu planlamak için bizimle iletişime geçebilir veya "
            f"platform üzerinden uygun bir saat seçebilirsiniz.\n\n"
            f"Anlayışınız için teşekkür ederiz.\n"
            f"FizyoTech Ekibi"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            fail_silently=False,
        )
        logger.info("Day cancellation email sent to %s", patient.email)
        return True
    except Exception:
        logger.exception(
            "Failed to send day cancellation email for patient %s", patient_id
        )
        return False


def _send_emails_async(grouped: dict, target_date_iso: str, reason: str) -> int:
    sent = 0
    for patient_id, details in grouped.items():
        if _send_day_cancellation_email(patient_id, target_date_iso, reason, details):
            sent += 1
    return sent


def _send_day_cancellation_push(grouped: dict, target_date_iso: str, reason: str):
    """Günü iptal edilen her hastaya push bildirimi gönderir."""
    try:
        from datetime import date as date_cls

        from accounts.push_service import send_push_to_users

        date_label = date_cls.fromisoformat(target_date_iso).strftime("%d.%m.%Y")
        for patient_id in grouped:
            send_push_to_users(
                patient_id,
                title=f"{date_label} dersiniz iptal edildi",
                body=reason or "Bu tarihteki randevularınız iptal edilmiştir.",
                data={"link": "/hesabim/randevular"},
            )
    except Exception:
        logger.exception("Gün iptali push bildirimleri gönderilemedi.")


@transaction.atomic
def cancel_day(target_date, reason: str, admin_user, add_holiday: bool = True):
    appointments = list(
        Appointment.objects.filter(
            appointment_datetime__date=target_date,
            status__in=ACTIVE_STATUSES,
        )
        .select_related("patient", "doctor")
        .order_by("appointment_datetime")
    )

    if not appointments:
        return {
            "cancelled_count": 0,
            "emails_sent": 0,
            "patient_count": 0,
        }

    grouped: dict[int, list[dict]] = defaultdict(list)

    for appt in appointments:
        local_dt = timezone.localtime(appt.appointment_datetime)
        grouped[appt.patient_id].append(
            {
                "time": local_dt.strftime("%H:%M"),
                "doctor_name": appt.doctor.get_full_name() or appt.doctor.username,
            }
        )
        appt.status = AppointmentStatus.CANCELLED
        appt.cancellation_reason = reason
        appt._notification_actor = admin_user
        appt._skip_admin_notification = True
        appt.save(
            update_fields=["status", "cancellation_reason", "updated_at"]
        )

    if add_holiday:
        ClinicHoliday.objects.update_or_create(
            date=target_date,
            defaults={"name": reason[:120] if reason else "Gün iptali"},
        )

    record = DayCancellation.objects.create(
        date=target_date,
        reason=reason,
        cancelled_by=admin_user,
        appointments_cancelled=len(appointments),
        emails_sent=0,
    )

    target_date_iso = target_date.isoformat()
    grouped_copy = dict(grouped)

    def send_and_update():
        sent = _send_emails_async(grouped_copy, target_date_iso, reason)
        DayCancellation.objects.filter(pk=record.pk).update(emails_sent=sent)
        _send_day_cancellation_push(grouped_copy, target_date_iso, reason)

    thread = threading.Thread(target=send_and_update, daemon=True)
    thread.start()

    return {
        "cancelled_count": len(appointments),
        "emails_scheduled": len(grouped),
        "patient_count": len(grouped),
        "day_cancellation_id": record.id,
    }
