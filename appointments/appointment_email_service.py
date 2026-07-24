import logging
import threading
from email.mime.base import MIMEBase
from email import encoders

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from .models import Appointment

logger = logging.getLogger(__name__)


def _format_datetime(dt) -> str:
    local_dt = timezone.localtime(dt)
    return local_dt.strftime("%d.%m.%Y %H:%M")


def _ical_datetime(dt) -> str:
    """UTC datetime string for iCalendar."""
    import datetime
    utc_dt = dt.astimezone(datetime.timezone.utc)
    return utc_dt.strftime("%Y%m%dT%H%M%SZ")


def _build_ics(appointment, method: str) -> bytes:
    """Build .ics content for METHOD:REQUEST or METHOD:CANCEL."""
    import datetime
    dt = appointment.appointment_datetime
    dtstart = _ical_datetime(dt)
    dtend = _ical_datetime(dt + datetime.timedelta(hours=1))
    dtstamp = _ical_datetime(timezone.now())
    uid = appointment.ical_uid
    doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
    patient_name = appointment.patient.get_full_name() or appointment.patient.username

    if method == "CANCEL":
        summary = f"İptal: JFS Method Randevu — Dr. {doctor_name}"
        status_line = "STATUS:CANCELLED"
    else:
        summary = f"JFS Method Randevu — Dr. {doctor_name}"
        status_line = "STATUS:CONFIRMED"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JFS Method//TR",
        f"METHOD:{method}",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:Hasta: {patient_name}",
        "LOCATION:JFS Method Klinik",
        status_line,
        f"SEQUENCE:{'1' if method == 'CANCEL' else '0'}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines).encode("utf-8")


def _send_email_with_ics(subject: str, message: str, recipient: str, ics_bytes: bytes, ics_filename: str) -> bool:
    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.attach(ics_filename, ics_bytes, "text/calendar")
        email.send(fail_silently=False)
        logger.info("Appointment email sent to %s — %s", recipient, subject)
        return True
    except Exception:
        logger.exception("Failed to send appointment email to %s", recipient)
        return False


def _send_plain_email(subject: str, message: str, recipient: str) -> bool:
    try:
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        email.send(fail_silently=False)
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
            return

        doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
        dt_label = _format_datetime(appointment.appointment_datetime)

        subject = "JFS Method — Randevu Talebiniz Alındı"
        message = (
            f"Sayın {patient.get_full_name() or patient.username},\n\n"
            f"Randevu talebiniz başarıyla alınmıştır.\n\n"
            f"Tarih/Saat: {dt_label}\n"
            f"Doktor: Dr. {doctor_name}\n"
            f"Durum: Onay bekliyor\n\n"
            f"Klinik tarafından onaylandığında ayrıca bilgilendirileceksiniz.\n"
            f"Randevularınızı web sitesindeki «Randevularım» bölümünden takip edebilirsiniz.\n\n"
            f"JFS Method Ekibi"
        )
        _send_plain_email(subject, message, patient.email)
    except Appointment.DoesNotExist:
        logger.warning("Appointment %s not found for creation email", appointment_id)


def send_appointment_approved_email(appointment_id: int):
    try:
        appointment = Appointment.objects.select_related("patient", "doctor").get(
            pk=appointment_id
        )
        patient = appointment.patient
        if not patient.email:
            return

        doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
        dt_label = _format_datetime(appointment.appointment_datetime)

        subject = "JFS Method — Randevunuz Onaylandı"
        message = (
            f"Sayın {patient.get_full_name() or patient.username},\n\n"
            f"Randevunuz onaylanmıştır.\n\n"
            f"Tarih/Saat: {dt_label}\n"
            f"Doktor: Dr. {doctor_name}\n\n"
            f"Bu e-postaya ekli takvim dosyasını açarak randevuyu takviminize ekleyebilirsiniz.\n"
            f"(Apple Takvim ve Outlook destekler. Google Calendar için randevularım sayfasındaki «Takvime Ekle» butonunu kullanın.)\n\n"
            f"Değişiklik veya iptal için web sitesinden «Randevularım» bölümünü kullanabilirsiniz.\n\n"
            f"JFS Method Ekibi"
        )
        ics = _build_ics(appointment, "REQUEST")
        _send_email_with_ics(subject, message, patient.email, ics, "randevu.ics")
    except Appointment.DoesNotExist:
        logger.warning("Appointment %s not found for approval email", appointment_id)


def send_appointment_cancelled_email(appointment_id: int):
    try:
        appointment = Appointment.objects.select_related("patient", "doctor").get(
            pk=appointment_id
        )
        patient = appointment.patient
        if not patient.email:
            return

        doctor_name = appointment.doctor.get_full_name() or appointment.doctor.username
        dt_label = _format_datetime(appointment.appointment_datetime)

        subject = "JFS Method — Randevunuz İptal Edildi"
        message = (
            f"Sayın {patient.get_full_name() or patient.username},\n\n"
            f"Aşağıdaki randevunuz iptal edilmiştir.\n\n"
            f"Tarih/Saat: {dt_label}\n"
            f"Doktor: Dr. {doctor_name}\n\n"
            f"Bu e-postaya ekli dosyayı açarak randevuyu takviminizden otomatik olarak kaldırabilirsiniz.\n"
            f"(Apple Takvim ve Outlook destekler.)\n\n"
            f"Yeni randevu almak için web sitesindeki «Randevularım» bölümünü kullanabilirsiniz.\n\n"
            f"JFS Method Ekibi"
        )
        ics = _build_ics(appointment, "CANCEL")
        _send_email_with_ics(subject, message, patient.email, ics, "randevu-iptal.ics")
    except Appointment.DoesNotExist:
        logger.warning("Appointment %s not found for cancellation email", appointment_id)


def schedule_appointment_created_email(appointment_id: int):
    threading.Thread(target=send_appointment_created_email, args=(appointment_id,), daemon=True).start()


def schedule_appointment_approved_email(appointment_id: int):
    threading.Thread(target=send_appointment_approved_email, args=(appointment_id,), daemon=True).start()


def schedule_appointment_cancelled_email(appointment_id: int):
    threading.Thread(target=send_appointment_cancelled_email, args=(appointment_id,), daemon=True).start()
