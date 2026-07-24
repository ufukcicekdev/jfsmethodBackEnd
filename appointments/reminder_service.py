"""Yaklaşan randevular için hatırlatma push bildirimleri.

Hatırlatma pencereleri admin panelinden yapılandırılır (ClinicScheduleSettings):
  - reminder_24h_enabled: 24 saat öncesi
  - reminder_1h_enabled: 1 saat öncesi
  - reminder_custom_minutes: özel süre (0 = kapalı)

`send_due_reminders()` periyodik olarak (cron) çalıştırılmak üzere
tasarlanmıştır. Her randevu için her pencere yalnızca bir kez gönderilir.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from .models import Appointment, AppointmentStatus, ClinicScheduleSettings

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = [AppointmentStatus.PENDING, AppointmentStatus.APPROVED]


def _get_settings():
    return ClinicScheduleSettings.objects.filter(pk=1).first() or ClinicScheduleSettings()


def _format_dt(dt):
    return timezone.localtime(dt).strftime("%d.%m.%Y %H:%M")


def _send_reminder(appointment, label):
    from accounts.push_service import send_push_to_users

    dt_label = _format_dt(appointment.appointment_datetime)
    doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
    send_push_to_users(
        appointment.patient,
        title="Randevu hatırlatması",
        body=f"{label} randevunuz var: {dt_label} (Dr. {doctor_name}).",
        data={
            "link": "/hesabim/randevular",
            "appointment_id": appointment.pk,
        },
    )


def send_due_reminders():
    """Zamanı yaklaşan randevular için hatırlatma gönderir."""
    now = timezone.now()
    cfg = _get_settings()
    sent_24h = 0
    sent_1h = 0
    sent_custom = 0

    # --- 1 saat penceresi ---
    if cfg.reminder_1h_enabled:
        one_hour_qs = (
            Appointment.objects.filter(
                status__in=ACTIVE_STATUSES,
                reminder_1h_sent=False,
                appointment_datetime__gt=now,
                appointment_datetime__lte=now + timedelta(hours=1),
            )
            .select_related("patient", "doctor")
        )
        for appt in one_hour_qs:
            _send_reminder(appt, "1 saat içinde")
            appt.reminder_1h_sent = True
            appt.reminder_24h_sent = True  # 24h penceresi de geçmiş say
            appt.save(update_fields=["reminder_1h_sent", "reminder_24h_sent"])
            sent_1h += 1

    # --- 24 saat penceresi ---
    if cfg.reminder_24h_enabled:
        day_qs = (
            Appointment.objects.filter(
                status__in=ACTIVE_STATUSES,
                reminder_24h_sent=False,
                appointment_datetime__gt=now + timedelta(hours=1),
                appointment_datetime__lte=now + timedelta(hours=24),
            )
            .select_related("patient", "doctor")
        )
        for appt in day_qs:
            _send_reminder(appt, "Yarın")
            appt.reminder_24h_sent = True
            appt.save(update_fields=["reminder_24h_sent"])
            sent_24h += 1

    # --- Özel süre penceresi ---
    if cfg.reminder_custom_minutes and cfg.reminder_custom_minutes > 0:
        window = timedelta(minutes=cfg.reminder_custom_minutes)
        # 1h ile çakışmayı önle: custom pencere 1h'den büyükse 1h'nin üstünden başla
        lower_bound = now + timedelta(hours=1) if cfg.reminder_custom_minutes > 60 else now
        custom_qs = (
            Appointment.objects.filter(
                status__in=ACTIVE_STATUSES,
                reminder_custom_sent=False,
                appointment_datetime__gt=lower_bound,
                appointment_datetime__lte=now + window,
            )
            .select_related("patient", "doctor")
        )
        minutes = cfg.reminder_custom_minutes
        if minutes >= 60:
            label = f"{minutes // 60} saat içinde"
        else:
            label = f"{minutes} dakika içinde"

        for appt in custom_qs:
            _send_reminder(appt, label)
            appt.reminder_custom_sent = True
            appt.save(update_fields=["reminder_custom_sent"])
            sent_custom += 1

    if sent_24h or sent_1h or sent_custom:
        logger.info(
            "Randevu hatırlatmaları gönderildi: 24h=%s, 1h=%s, özel=%s",
            sent_24h, sent_1h, sent_custom,
        )

    return {"sent_24h": sent_24h, "sent_1h": sent_1h, "sent_custom": sent_custom}


def send_eod_attendance_reminders():
    """Gün sonunda katılım işaretlenmemiş randevular için admine push gönderir."""
    from accounts.push_service import send_push_to_staff

    now = timezone.now()
    today = timezone.localdate()

    unmarked = (
        Appointment.objects.filter(
            status__in=ACTIVE_STATUSES,
            appointment_datetime__date=today,
            appointment_datetime__lt=now,
        )
        .select_related("patient", "doctor")
    )

    count = unmarked.count()
    if count == 0:
        return {"notified": 0}

    patient_names = ", ".join(
        a.patient.get_full_name() or a.patient.username
        for a in unmarked[:5]
    )
    suffix = f" ve {count - 5} diğeri" if count > 5 else ""

    send_push_to_staff(
        title=f"Bugün {count} randevunun katılımı işaretlenmedi",
        body=f"{patient_names}{suffix} — Geldi/Gelmedi olarak işaretleyin.",
        data={"link": "/panel/randevular?status=approved"},
    )

    logger.info("Gün sonu katılım hatırlatması gönderildi: %s randevu", count)
    return {"notified": count}
