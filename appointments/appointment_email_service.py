import logging
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Appointment

logger = logging.getLogger(__name__)


def _format_datetime(dt) -> str:
    local_dt = timezone.localtime(dt)
    return local_dt.strftime("%d.%m.%Y %H:%M")


def _send_email(subject: str, message: str, recipient: str) -> bool:
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        logger.info("Appointment email sent to %s — %s", recipient, subject)
        return True
    except Exception:
        logger.exception("Failed to send appointment email to %s", recipient)
        return False


def send_appointment_created_email(appointment_id: int):
    try:
        appointment = Appointment.objects.select_related("patient", "doctor").get(
            pk=appointment_id
        )
        patient = appointment.patient
        if not patient.email:
            logger.warning(
                "Cannot send creation email: patient %s has no email",
                patient.username,
            )
            return

        doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
        dt_label = _format_datetime(appointment.appointment_datetime)

        subject = "FizyoTech — Randevu Talebiniz Alındı"
        message = (
            f"Sayın {patient.get_full_name() or patient.username},\n\n"
            f"Randevu talebiniz başarıyla alınmıştır.\n\n"
            f"Tarih/Saat: {dt_label}\n"
            f"Doktor: Dr. {doctor_name}\n"
            f"Durum: Onay bekliyor\n\n"
            f"Klinik tarafından onaylandığında ayrıca bilgilendirileceksiniz.\n"
            f"Randevularınızı web sitesindeki «Randevularım» bölümünden takip edebilirsiniz.\n\n"
            f"FizyoTech Ekibi"
        )
        _send_email(subject, message, patient.email)
    except Appointment.DoesNotExist:
        logger.warning("Appointment %s not found for creation email", appointment_id)


def send_appointment_approved_email(appointment_id: int):
    try:
        appointment = Appointment.objects.select_related("patient", "doctor").get(
            pk=appointment_id
        )
        patient = appointment.patient
        if not patient.email:
            logger.warning(
                "Cannot send approval email: patient %s has no email",
                patient.username,
            )
            return

        doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
        dt_label = _format_datetime(appointment.appointment_datetime)

        subject = "FizyoTech — Randevunuz Onaylandı"
        message = (
            f"Sayın {patient.get_full_name() or patient.username},\n\n"
            f"Randevunuz onaylanmıştır.\n\n"
            f"Tarih/Saat: {dt_label}\n"
            f"Doktor: Dr. {doctor_name}\n\n"
            f"Lütfen randevu saatinde kliniğimize gelmeyi unutmayın.\n"
            f"Değişiklik veya iptal için web sitesinden «Randevularım» bölümünü kullanabilirsiniz.\n\n"
            f"FizyoTech Ekibi"
        )
        _send_email(subject, message, patient.email)
    except Appointment.DoesNotExist:
        logger.warning("Appointment %s not found for approval email", appointment_id)


def schedule_appointment_created_email(appointment_id: int):
    thread = threading.Thread(
        target=send_appointment_created_email,
        args=(appointment_id,),
        daemon=True,
    )
    thread.start()


def schedule_appointment_approved_email(appointment_id: int):
    thread = threading.Thread(
        target=send_appointment_approved_email,
        args=(appointment_id,),
        daemon=True,
    )
    thread.start()
