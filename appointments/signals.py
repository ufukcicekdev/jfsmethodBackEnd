import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Appointment, AppointmentStatus

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Appointment)
def capture_original_state(sender, instance, **kwargs):
    if instance.pk:
        try:
            original = Appointment.objects.get(pk=instance.pk)
            instance._original_datetime = original.appointment_datetime
            instance._original_status = original.status
        except Appointment.DoesNotExist:
            instance._original_datetime = None
            instance._original_status = None
    else:
        instance._original_datetime = None
        instance._original_status = None


def _send_postponement_email(appointment_id: int, original_datetime_iso: str):
    try:
        appointment = Appointment.objects.select_related("patient", "doctor").get(
            pk=appointment_id
        )
        patient = appointment.patient
        doctor = appointment.doctor

        if not patient.email:
            logger.warning(
                "Cannot send postponement email: patient %s has no email",
                patient.username,
            )
            return

        from django.utils import timezone

        original_dt = timezone.datetime.fromisoformat(original_datetime_iso)
        if timezone.is_naive(original_dt):
            original_dt = timezone.make_aware(original_dt)

        subject = "FizyoTech — Randevunuz Ertelendi"
        message = (
            f"Sayın {patient.get_full_name() or patient.username},\n\n"
            f"Randevunuz ertelenmiştir.\n\n"
            f"Orijinal Tarih/Saat: {original_dt.strftime('%d.%m.%Y %H:%M')}\n"
            f"Yeni Tarih/Saat: {appointment.appointment_datetime.strftime('%d.%m.%Y %H:%M')}\n"
            f"Doktor: {doctor.get_full_name() or doctor.username}\n\n"
            f"Açıklama: {appointment.note}\n\n"
            f"Herhangi bir sorunuz için bizimle iletişime geçebilirsiniz.\n\n"
            f"FizyoTech Ekibi"
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[patient.email],
            fail_silently=False,
        )
        logger.info("Postponement email sent to %s", patient.email)
    except Exception:
        logger.exception(
            "Failed to send postponement email for appointment %s", appointment_id
        )


@receiver(post_save, sender=Appointment)
def trigger_postponement_email(sender, instance, created, **kwargs):
    if created:
        return

    original_status = getattr(instance, "_original_status", None)
    original_datetime = getattr(instance, "_original_datetime", None)

    if (
        original_status is not None
        and instance.status == AppointmentStatus.POSTPONED
        and original_status != AppointmentStatus.POSTPONED
        and original_datetime is not None
    ):
        thread = threading.Thread(
            target=_send_postponement_email,
            args=(instance.pk, original_datetime.isoformat()),
            daemon=True,
        )
        thread.start()


def _format_appt_dt(instance):
    from django.utils import timezone

    return timezone.localtime(instance.appointment_datetime).strftime(
        "%d.%m.%Y %H:%M"
    )


def _push_patient_status_change(instance, new_status):
    """Personel bir randevuyu güncellediğinde hastaya push gönderir."""
    from accounts.push_service import send_push_to_users

    dt_label = _format_appt_dt(instance)
    messages = {
        AppointmentStatus.APPROVED: (
            "Randevunuz onaylandı",
            f"{dt_label} tarihli randevunuz onaylandı.",
        ),
        AppointmentStatus.POSTPONED: (
            "Randevunuz ertelendi",
            f"Randevunuz {dt_label} olarak güncellendi.",
        ),
        AppointmentStatus.COMPLETED: (
            "Randevunuz tamamlandı",
            f"{dt_label} tarihli randevunuz tamamlandı olarak işaretlendi.",
        ),
        AppointmentStatus.CANCELLED: (
            "Randevunuz iptal edildi",
            f"{dt_label} tarihli randevunuz iptal edildi.",
        ),
        AppointmentStatus.NO_SHOW: (
            "Randevunuza gelmediniz",
            f"{dt_label} tarihli randevunuza katılım sağlanmadı.",
        ),
    }
    entry = messages.get(new_status)
    if not entry:
        return
    title, body = entry
    send_push_to_users(
        instance.patient,
        title=title,
        body=body,
        data={
            "link": "/hesabim/randevular",
            "notification_type": "appointment",
            "appointment_id": instance.pk,
        },
    )


@receiver(post_save, sender=Appointment)
def handle_appointment_notifications(sender, instance, created, **kwargs):
    from accounts.push_service import send_push_to_staff

    from .appointment_email_service import (
        schedule_appointment_approved_email,
        schedule_appointment_created_email,
    )
    from .notification_service import (
        notify_appointment_cancelled,
        notify_appointment_created,
        notify_appointment_status_change,
    )

    if created:
        actor = getattr(instance, "_notification_actor", None)
        if actor and actor.is_staff:
            # Admin, hasta adına randevu oluşturdu -> hastaya bildir
            from accounts.push_service import send_push_to_users

            send_push_to_users(
                instance.patient,
                title="Randevunuz oluşturuldu",
                body=(
                    f"{_format_appt_dt(instance)} tarihli randevunuz "
                    "klinik tarafından oluşturuldu."
                ),
                data={
                    "link": "/hesabim/randevular",
                    "notification_type": "appointment",
                    "appointment_id": instance.pk,
                },
            )
            return

        notify_appointment_created(instance)
        schedule_appointment_created_email(instance.pk)
        patient_name = (
            instance.patient.get_full_name() or instance.patient.username
        )
        send_push_to_staff(
            title="Yeni randevu talebi",
            body=f"{patient_name} — {_format_appt_dt(instance)}",
            data={"link": "/panel/randevular", "appointment_id": instance.pk},
        )
        return

    if getattr(instance, "_skip_admin_notification", False):
        return

    original_status = getattr(instance, "_original_status", None)
    if original_status is None or original_status == instance.status:
        return

    actor = getattr(instance, "_notification_actor", None)

    if instance.status == AppointmentStatus.CANCELLED:
        notify_appointment_cancelled(instance, actor or instance.patient)
        if actor and actor.is_staff:
            # Admin iptal etti -> hastaya bildir
            _push_patient_status_change(instance, AppointmentStatus.CANCELLED)
        else:
            # Hasta iptal etti -> personele bildir
            patient_name = (
                instance.patient.get_full_name() or instance.patient.username
            )
            send_push_to_staff(
                title="Randevu iptal edildi",
                body=f"{patient_name} — {_format_appt_dt(instance)} randevusunu iptal etti.",
                data={"link": "/panel/randevular", "appointment_id": instance.pk},
            )
        return

    if (
        instance.status == AppointmentStatus.APPROVED
        and original_status != AppointmentStatus.APPROVED
    ):
        schedule_appointment_approved_email(instance.pk)

    if actor and actor.is_staff:
        # Personel kaynaklı durum değişikliği -> hastaya push
        _push_patient_status_change(instance, instance.status)
        return

    notify_appointment_status_change(
        instance, original_status, instance.status, actor
    )
