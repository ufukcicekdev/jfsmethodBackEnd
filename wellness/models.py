import uuid

from django.conf import settings
from django.db import models


class CategoryType(models.TextChoices):
    EXERCISE = "exercise", "Egzersiz"
    DIET = "diet", "Diyet Programı"
    FOOD = "food", "Besin"


class Category(models.Model):
    name = models.CharField(max_length=120)
    category_type = models.CharField(max_length=16, choices=CategoryType.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"

    def __str__(self):
        return self.name


def exercise_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() or "jpg"
    return f"exercises/{uuid.uuid4().hex}.{ext}"


def exercise_video_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() or "mp4"
    return f"exercises/videos/{uuid.uuid4().hex}.{ext}"


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
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="exercises"
    )
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=exercise_image_path, null=True, blank=True)
    video = models.FileField(upload_to=exercise_video_path, null=True, blank=True)
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

    def save(self, *args, **kwargs):
        from wellness.image_utils import convert_to_webp
        convert_to_webp(self.image)
        super().save(*args, **kwargs)

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
    send_times = models.JSONField(default=list, help_text='["HH:MM", ...] formatında saat listesi')
    days_of_week = models.JSONField(default=list, help_text="[0-6], 0=Pzt")
    is_enabled = models.BooleanField(default=True)
    last_triggered_times = models.JSONField(default=dict, help_text='{"YYYY-MM-DD:HH:MM": true} çift gönderim engeli')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["notification_type"]
        verbose_name = "Bildirim Zamanlaması"
        verbose_name_plural = "Bildirim Zamanlamaları"

    def __str__(self):
        return f"{self.get_notification_type_display()} — {', '.join(self.send_times)}"


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


class ProgramType(models.TextChoices):
    WEEKLY = "weekly", "Haftalık Plan"
    SEQUENTIAL = "sequential", "Sıralı Günler"


class ExerciseProgram(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    program_type = models.CharField(max_length=16, choices=ProgramType.choices, default=ProgramType.WEEKLY)
    difficulty = models.CharField(max_length=16, choices=ExerciseDifficulty.choices, default=ExerciseDifficulty.EASY)
    duration_weeks = models.PositiveSmallIntegerField(default=4, help_text="Tahmini süre (hafta)")
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="exercise_programs")
    thumbnail = models.ImageField(upload_to="program_thumbnails/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        from wellness.image_utils import convert_to_webp
        convert_to_webp(self.thumbnail)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ExerciseProgramDay(models.Model):
    program = models.ForeignKey(ExerciseProgram, on_delete=models.CASCADE, related_name="days")
    # weekly → 0=Pzt, 1=Sal, ..., 6=Paz | sequential → 1,2,3...
    day_number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "day_number"]
        unique_together = [("program", "day_number")]

    def __str__(self):
        return f"{self.program.name} — Gün {self.day_number}"


class ExerciseProgramItem(models.Model):
    day = models.ForeignKey(ExerciseProgramDay, on_delete=models.CASCADE, related_name="items")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="program_items")
    sets = models.PositiveSmallIntegerField(default=3)
    reps = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_seconds = models.PositiveSmallIntegerField(null=True, blank=True)
    rest_seconds = models.PositiveSmallIntegerField(default=60)
    note = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]

    def __str__(self):
        return f"{self.day} — {self.exercise.title}"


class ProductPackage(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    exercise_program = models.ForeignKey(ExerciseProgram, null=True, blank=True, on_delete=models.SET_NULL, related_name="packages")
    diet_program = models.ForeignKey("accounts.DietProgram", null=True, blank=True, on_delete=models.SET_NULL, related_name="packages")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Bilgi amaçlı fiyat etiketi")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserPackageAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="package_assignments")
    package = models.ForeignKey(ProductPackage, on_delete=models.CASCADE, related_name="assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_packages")
    assigned_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        unique_together = [("user", "package")]

    def __str__(self):
        return f"{self.user.username} → {self.package.name}"


# ── Meal Tracking ─────────────────────────────────────────────────────────────

def meal_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1]
    return f"meal_photos/{instance.user_id}/{uuid.uuid4()}.{ext}"


class MealType(models.TextChoices):
    BREAKFAST = "breakfast", "Kahvaltı"
    LUNCH = "lunch", "Öğle"
    DINNER = "dinner", "Akşam"
    SNACK = "snack", "Ara Öğün"


class MealLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_logs")
    meal_type = models.CharField(max_length=16, choices=MealType.choices)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to=meal_photo_path, null=True, blank=True)
    logged_at = models.DateTimeField()
    admin_note = models.TextField(blank=True)
    admin_note_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="meal_notes")
    admin_note_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at"]

    def save(self, *args, **kwargs):
        from wellness.image_utils import convert_to_webp
        convert_to_webp(self.photo)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} — {self.get_meal_type_display()} {self.logged_at.date()}"


# ── Program Exercise Log ──────────────────────────────────────────────────────

class ProgramExerciseLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="program_exercise_logs")
    program_item = models.ForeignKey(ExerciseProgramItem, on_delete=models.CASCADE, related_name="logs")
    # Which day-cycle this belongs to (for sequential: iteration number, for weekly: ISO week number)
    cycle = models.PositiveSmallIntegerField(default=1, help_text="Hafta/döngü numarası")
    completed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=500, blank=True)
    difficulty_felt = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Kullanıcının hissettiği zorluk (1-5)")

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.username} — {self.program_item.exercise.title} ({self.completed_at.date()})"


# ── Per-User Notification Schedule (package-based) ────────────────────────────

class UserNotificationSchedule(models.Model):
    TYPE_CHOICES = [
        ("meal",     "Öğün Hatırlatması"),
        ("exercise", "Egzersiz Hatırlatması"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_schedules")
    package_assignment = models.ForeignKey(UserPackageAssignment, null=True, blank=True, on_delete=models.SET_NULL, related_name="notification_schedules")
    notification_type = models.CharField(max_length=16, choices=TYPE_CHOICES)
    title = models.CharField(max_length=120)
    message = models.TextField()
    send_times = models.JSONField(default=list, help_text='["HH:MM", ...]')
    days_of_week = models.JSONField(default=list, help_text="[0-6], boş = her gün")
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["notification_type", "user"]

    def __str__(self):
        return f"{self.user.username} — {self.get_notification_type_display()}"


class ProgramMealEntry(models.Model):
    MEAL_TYPES = [
        ("sabah",   "Kahvaltı"),
        ("ara1",    "Ara Öğün 1"),
        ("ogle",    "Öğle"),
        ("ara2",    "Ara Öğün 2"),
        ("aksam",   "Akşam"),
        ("gece",    "Gece"),
    ]
    day = models.ForeignKey(ExerciseProgramDay, on_delete=models.CASCADE, related_name="meal_entries")
    meal_type = models.CharField(max_length=16, choices=MEAL_TYPES)
    diet_items = models.ManyToManyField(
        "accounts.DietItem",
        blank=True,
        related_name="program_meal_entries",
        help_text="Kütüphaneden seçilen besinler",
    )
    notification_time = models.TimeField(null=True, blank=True, help_text="Bildirim saati (HH:MM)")
    description = models.TextField(blank=True, help_text="Ek notlar / serbest metin")
    calories = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Tahmini kalori (kcal)")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["notification_time", "sort_order", "meal_type"]

    def __str__(self):
        return f"{self.day} — {self.get_meal_type_display()}"
