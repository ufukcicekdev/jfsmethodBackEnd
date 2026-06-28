from django.utils import timezone

from .models import AdminNotification, NotificationType


def _format_datetime(dt):
    local = timezone.localtime(dt)
    return local.strftime("%d.%m.%Y %H:%M")


def create_admin_notification(
    *,
    notification_type: str,
    title: str,
    message: str,
    appointment=None,
    actor=None,
):
    return AdminNotification.objects.create(
        notification_type=notification_type,
        title=title,
        message=message,
        appointment=appointment,
        actor=actor,
    )


def notify_appointment_created(appointment):
    patient = appointment.patient
    patient_name = patient.get_full_name() or patient.username
    doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
    create_admin_notification(
        notification_type=NotificationType.APPOINTMENT_NEW,
        title="Yeni randevu talebi",
        message=(
            f"{patient_name} — {_format_datetime(appointment.appointment_datetime)} "
            f"(Dr. {doctor_name})"
        ),
        appointment=appointment,
        actor=patient,
    )


def notify_appointment_cancelled(appointment, actor):
    patient_name = appointment.patient.get_full_name() or appointment.patient.username
    actor_name = actor.get_full_name() or actor.username
    create_admin_notification(
        notification_type=NotificationType.APPOINTMENT_CANCELLED,
        title="Randevu iptal edildi",
        message=(
            f"{patient_name} — {_format_datetime(appointment.appointment_datetime)} "
            f"(İptal: {actor_name})"
        ),
        appointment=appointment,
        actor=actor,
    )


def notify_appointment_status_change(appointment, old_status, new_status, actor=None):
    if old_status == new_status:
        return

    patient_name = appointment.patient.get_full_name() or appointment.patient.username
    dt_label = _format_datetime(appointment.appointment_datetime)

    mapping = {
        NotificationType.APPOINTMENT_APPROVED: (
            "Randevu onaylandı",
            f"{patient_name} — {dt_label}",
        ),
        NotificationType.APPOINTMENT_POSTPONED: (
            "Randevu ertelendi",
            f"{patient_name} — yeni saat: {dt_label}",
        ),
        NotificationType.APPOINTMENT_COMPLETED: (
            "Randevu tamamlandı",
            f"{patient_name} — {dt_label}",
        ),
    }

    type_by_status = {
        "approved": NotificationType.APPOINTMENT_APPROVED,
        "postponed": NotificationType.APPOINTMENT_POSTPONED,
        "completed": NotificationType.APPOINTMENT_COMPLETED,
    }

    notification_type = type_by_status.get(new_status)
    if not notification_type:
        return

    title, message = mapping[notification_type]
    create_admin_notification(
        notification_type=notification_type,
        title=title,
        message=message,
        appointment=appointment,
        actor=actor,
    )


def notify_patient_registered(user):
    name = user.get_full_name() or user.username
    create_admin_notification(
        notification_type=NotificationType.PATIENT_REGISTERED,
        title="Yeni öğrenci kaydı",
        message=f"{name} ({user.email}) platforma kayıt oldu.",
        actor=user,
    )
