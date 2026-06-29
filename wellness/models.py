import uuid

from django.conf import settings
from django.db import models


def exercise_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() or "jpg"
    return f"exercises/{uuid.uuid4().hex}.{ext}"


class BodyRegion(models.TextChoices):
    NECK = "neck", "Boyun"
    SHOULDER_LEFT = "shoulder_left", "Sol Omuz"
    SHOULDER_RIGHT = "shoulder_right", "Sağ Omuz"
    UPPER_BACK = "upper_back", "Üst Sırt"
    LOWER_BACK = "lower_back", "Bel"
    HIP_LEFT = "hip_left", "Sol Kalça"
    HIP_RIGHT = "hip_right", "Sağ Kalça"
    KNEE_LEFT = "knee_left", "Sol Diz"
    KNEE_RIGHT = "knee_right", "Sağ Diz"


class ExerciseDifficulty(models.TextChoices):
    EASY = "easy", "Kolay"
    MEDIUM = "medium", "Orta"
    HARD = "hard", "Zor"


class ExerciseFrequency(models.TextChoices):
    DAILY = "daily", "Her gün"
    EVERY_OTHER_DAY = "every_other_day", "Gün aşırı"
    WEEKLY = "weekly", "Haftada 3"
    AS_NEEDED = "as_needed", "İhtiyaç halinde"


class Exercise(models.Model):
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=exercise_image_path, null=True, blank=True)
    instructions = models.TextField(
        help_text="Adım adım hareket talimatları"
    )
    target_region = models.CharField(
        max_length=32,
        choices=BodyRegion.choices,
        blank=True,
    )
    duration_minutes = models.PositiveSmallIntegerField(default=10)
    sets = models.PositiveSmallIntegerField(default=3)
    reps = models.PositiveSmallIntegerField(default=10)
    difficulty = models.CharField(
        max_length=16,
        choices=ExerciseDifficulty.choices,
        default=ExerciseDifficulty.EASY,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class RegionPainLog(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pain_logs",
    )
    region = models.CharField(max_length=32, choices=BodyRegion.choices)
    pain_level = models.PositiveSmallIntegerField(
        help_text="0 = ağrı yok, 10 = çok şiddetli"
    )
    note = models.CharField(max_length=255, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [
            models.Index(fields=["patient", "region", "-recorded_at"]),
        ]

    def __str__(self):
        return f"{self.patient.username} — {self.get_region_display()}: {self.pain_level}"


class ExerciseAssignment(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_assignments",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_exercises",
    )
    therapist_note = models.TextField(
        blank=True,
        help_text="Terapistin ev programı notu",
    )
    frequency = models.CharField(
        max_length=24,
        choices=ExerciseFrequency.choices,
        default=ExerciseFrequency.DAILY,
    )
    is_active = models.BooleanField(default=True)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient.username} — {self.exercise.title}"


class DailyWaterLog(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="water_logs",
    )
    date = models.DateField()
    ml_consumed = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("patient", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.patient.username} — {self.date}: {self.ml_consumed}ml"


class DailyStepLog(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="step_logs",
    )
    date = models.DateField()
    step_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("patient", "date")]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.patient.username} — {self.date}: {self.step_count} adım"


class NotificationSchedule(models.Model):
    TYPE_CHOICES = [
        ("water",    "Su Hatırlatması"),
        ("steps",    "Adım Hatırlatması"),
        ("exercise", "Egzersiz Hatırlatması"),
        ("custom",   "Özel Mesaj"),
    ]
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120)
    message = models.TextField()
    send_time = models.TimeField()
    days_of_week = models.JSONField(default=list, help_text="[0-6], 0=Pzt")
    is_enabled = models.BooleanField(default=True)
    last_triggered_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["send_time"]
        verbose_name = "Bildirim Zamanlaması"
        verbose_name_plural = "Bildirim Zamanlamaları"

    def __str__(self):
        return f"{self.get_notification_type_display()} — {self.send_time}"


class ExerciseCompletion(models.Model):
    assignment = models.ForeignKey(
        ExerciseAssignment,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_completions",
    )
    pain_before = models.PositiveSmallIntegerField(null=True, blank=True)
    pain_after = models.PositiveSmallIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.patient.username} completed {self.assignment.exercise.title}"
