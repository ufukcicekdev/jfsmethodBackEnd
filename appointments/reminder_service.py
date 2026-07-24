"""Yaklaşan randevular için hatırlatma push bildirimleri.

İki hatırlatma penceresi desteklenir:
  - 24 saat öncesi (reminder_24h_sent)
  - 1 saat öncesi (reminder_1h_sent)

`send_due_reminders()` periyodik olarak (cron) çalıştırılmak üzere
tasarlanmıştır. Her randevu için her pencere yalnızca bir kez gönderilir.
"""

import logging
from datetime import timedelta

from django.utils import timezone

from .models import Appointment, AppointmentStatus

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = [AppointmentStatus.PENDING, AppointmentStatus.APPROVED]

REMINDER_WINDOW_24H = timedelta(hours=24)
REMINDER_WINDOW_1H = timedelta(hours=1)


def _format_dt(dt):
    return timezone.localtime(dt).strftime("%d.%m.%Y %H:%M")


def _send_reminder(appointment, label):
    from accounts.push_service import send_push_to_users

    dt_label = _format_dt(appointment.appointment_datetime)
    doctor_name = (
        appointment.doctor.get_full_name() or appointment.doctor.username
    )
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
    """Zamanı yaklaşan randevular için hatırlatma gönderir.

    Döndürür: {"sent_24h": int, "sent_1h": int}
    """
    now = timezone.now()
    sent_24h = 0
    sent_1h = 0

    # 1 saat penceresi: şimdi ile +1 saat arasındaki, henüz hatırlatılmamışlar
    one_hour_qs = (
        Appointment.objects.filter(
            status__in=ACTIVE_STATUSES,
            reminder_1h_sent=False,
            appointment_datetime__gt=now,
            appointment_datetime__lte=now + REMINDER_WINDOW_1H,
        )
        .select_related("patient", "doctor")
    )
    for appt in one_hour_qs:
        _send_reminder(appt, "1 saat içinde")
        # 1 saatlik hatırlatma gittiyse 24 saatliği de geçmiş say
        appt.reminder_1h_sent = True
        appt.reminder_24h_sent = True
        appt.save(update_fields=["reminder_1h_sent", "reminder_24h_sent"])
        sent_1h += 1

    # 24 saat penceresi: şimdi ile +24 saat arasındaki, 1h gönderilmemiş ve
    # 24h gönderilmemiş olanlar (1h penceresine girenler yukarıda elendi)
    day_qs = (
        Appointment.objects.filter(
            status__in=ACTIVE_STATUSES,
            reminder_24h_sent=False,
            appointment_datetime__gt=now + REMINDER_WINDOW_1H,
            appointment_datetime__lte=now + REMINDER_WINDOW_24H,
        )
        .select_related("patient", "doctor")
    )
    for appt in day_qs:
        _send_reminder(appt, "Yarın")
        appt.reminder_24h_sent = True
        appt.save(update_fields=["reminder_24h_sent"])
        sent_24h += 1

    if sent_24h or sent_1h:
        logger.info(
            "Randevu hatırlatmaları gönderildi: 24h=%s, 1h=%s",
            sent_24h,
            sent_1h,
        )

    return {"sent_24h": sent_24h, "sent_1h": sent_1h}


def send_eod_attendance_reminders():
    """Gün sonunda katılım işaretlenmemiş randevular için admine push gönderir.

    Bugünkü 'approved' veya 'pending' randevulardan saati geçmiş olanları bulur.
    Admin henüz 'completed' veya 'no_show' yapmamışsa bildirim gönderir.
    """
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
