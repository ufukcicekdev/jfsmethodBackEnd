from datetime import time

from django.conf import settings
from django.db import models


class AppointmentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    POSTPONED = "postponed", "Postponed"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"
    NO_SHOW = "no_show", "No Show"


class NotificationType(models.TextChoices):
    APPOINTMENT_NEW = "appointment_new", "Yeni Randevu"
    APPOINTMENT_CANCELLED = "appointment_cancelled", "Randevu İptali"
    APPOINTMENT_APPROVED = "appointment_approved", "Randevu Onayı"
    APPOINTMENT_POSTPONED = "appointment_postponed", "Randevu Ertelendi"
    APPOINTMENT_COMPLETED = "appointment_completed", "Randevu Tamamlandı"
    PATIENT_REGISTERED = "patient_registered", "Yeni Kayıt"


class AdminNotification(models.Model):
    notification_type = models.CharField(
        max_length=32,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=120)
    message = models.TextField()
    appointment = models.ForeignKey(
        "Appointment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({'okundu' if self.is_read else 'yeni'})"


class ClinicScheduleSettings(models.Model):
    slot_duration_minutes = models.PositiveIntegerField(default=30)
    slot_capacity = models.PositiveIntegerField(
        default=1,
        help_text="Aynı doktor ve saatte randevu alabilecek maksimum kişi sayısı",
    )

    class Meta:
        verbose_name = "Clinic Schedule Settings"
        verbose_name_plural = "Clinic Schedule Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f"Klinik ayarları ({self.slot_duration_minutes} dk slot)"


WEEKDAY_CHOICES = [
    (0, "Pazartesi"),
    (1, "Salı"),
    (2, "Çarşamba"),
    (3, "Perşembe"),
    (4, "Cuma"),
    (5, "Cumartesi"),
    (6, "Pazar"),
]

WEEKDAY_LABELS = dict(WEEKDAY_CHOICES)


class WorkingDay(models.Model):
    day_of_week = models.PositiveSmallIntegerField(
        choices=WEEKDAY_CHOICES,
        unique=True,
    )
    is_working = models.BooleanField(default=True)
    start_time = models.TimeField(default=time(9, 0))
    end_time = models.TimeField(default=time(18, 0))

    class Meta:
        verbose_name = "Working Day"
        verbose_name_plural = "Working Days"
        ordering = ["day_of_week"]

    @property
    def day_label(self):
        return WEEKDAY_LABELS[self.day_of_week]

    def __str__(self):
        status = "Açık" if self.is_working else "Kapalı"
        return f"{self.day_label} ({status})"


class ClinicHoliday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Clinic Holiday"
        verbose_name_plural = "Clinic Holidays"
        ordering = ["date"]

    def __str__(self):
        label = self.name or "Tatil"
        return f"{label} — {self.date:%Y-%m-%d}"


class Appointment(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_appointments",
        limit_choices_to={"is_staff": True},
    )
    package = models.ForeignKey(
        "accounts.SessionPackage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
    )
    appointment_datetime = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.PENDING,
    )
    note = models.TextField(
        blank=True,
        help_text="Doctor's comments or reason for status change",
    )
    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason when appointment is cancelled (e.g. day cancellation)",
    )
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["appointment_datetime"]
        indexes = [
            models.Index(fields=["appointment_datetime", "status"]),
            models.Index(fields=["patient", "status"]),
        ]

    def __str__(self):
        return (
            f"{self.patient.username} with Dr. {self.doctor.last_name} "
            f"@ {self.appointment_datetime:%Y-%m-%d %H:%M} [{self.status}]"
        )


class DayCancellation(models.Model):
    date = models.DateField()
    reason = models.TextField()
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="day_cancellations",
    )
    appointments_cancelled = models.PositiveIntegerField(default=0)
    emails_sent = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Gün iptali — {self.date:%Y-%m-%d}"