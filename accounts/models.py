import uuid

from django.conf import settings
from django.db import models


class PhotoCategory(models.TextChoices):
    POSTURE_FRONT = "posture_front", "Önden (Postür)"
    POSTURE_SIDE = "posture_side", "Yandan (Postür)"
    POSTURE_BACK = "posture_back", "Arkadan (Postür)"
    EXERCISE = "exercise", "Egzersiz"
    GENERAL = "general", "Genel"
    OTHER = "other", "Diğer"


def patient_photo_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower()
    return f"patient_photos/{instance.patient_id}/{uuid.uuid4().hex}.{ext}"


def posture_image_path(instance, filename):
    ext = filename.rsplit(".", 1)[-1].lower() or "png"
    return f"posture/{instance.patient_id}/{uuid.uuid4().hex}.{ext}"


class PackagePlan(models.Model):
    """Admin tarafından tanımlanan, yeniden kullanılabilir paket şablonu (katalog).

    Hastalara bu kataloğdan paket atanır. Atama sırasında ad/seans/fiyat
    hastanın paketine kopyalanır (snapshot), böylece sonradan plan değişse de
    geçmiş etkilenmez.
    """

    name = models.CharField(max_length=120)
    total_sessions = models.PositiveIntegerField(default=12)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="package_images/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paket Planı"
        verbose_name_plural = "Paket Planları"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.total_sessions} seans)"


class SessionPackage(models.Model):
    """Bir hastaya tanımlanan seans paketi (kota mantığı).

    Seanslar paketin içinde fiziksel olarak durmaz; paket yalnızca toplam hak
    sayısını tutar. Kullanılan = tamamlanan (completed) randevular. Gelmediği
    (no_show) randevular sayılır ama kotadan düşmez.
    """

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_packages",
    )
    plan = models.ForeignKey(
        "PackagePlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_packages",
    )
    name = models.CharField(
        max_length=120,
        blank=True,
        help_text="Örn. '12 Seanslık Fizyoterapi Paketi'",
    )
    total_sessions = models.PositiveIntegerField(default=12)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateField(null=True, blank=True)
    purchased_at = models.DateField()
    note = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_session_packages",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Session Package"
        verbose_name_plural = "Session Packages"
        ordering = ["-purchased_at", "-created_at"]
        indexes = [
            models.Index(fields=["patient", "is_active"]),
        ]

    def __str__(self):
        label = self.name or f"{self.total_sessions} seanslık paket"
        return f"{self.patient.username} — {label}"

    def _count(self, status):
        return self.appointments.filter(status=status).count()

    @property
    def used_sessions(self):
        return self.attendance_records.filter(status="came").count()

    @property
    def no_show_count(self):
        return self.attendance_records.filter(status="no_show").count()

    @property
    def scheduled_count(self):
        return self.appointments.filter(
            status__in=["pending", "approved"]
        ).count()

    @property
    def remaining_sessions(self):
        return max(0, self.total_sessions - self.used_sessions)


class FCMDevice(models.Model):
    """A registered web push (Firebase Cloud Messaging) device for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="fcm_devices",
    )
    token = models.CharField(max_length=512, unique=True)
    user_agent = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FCM Device"
        verbose_name_plural = "FCM Devices"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user.username} — {self.token[:16]}…"


class OnboardingQuestion(models.Model):
    class QuestionType(models.TextChoices):
        TEXT = "text", "Açık Metin"
        CHOICE = "choice", "Çoktan Seçmeli"
        SCALE = "scale", "Skala (1-10)"
        MULTI = "multi", "Çoklu Seçim"

    text = models.CharField(max_length=500)
    question_type = models.CharField(max_length=20, choices=QuestionType.choices, default=QuestionType.TEXT)
    options = models.JSONField(default=list, blank=True)
    is_required = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]


class OnboardingAnswer(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="onboarding_answers",
    )
    question = models.ForeignKey(OnboardingQuestion, on_delete=models.CASCADE, related_name="answers")
    answer = models.JSONField()
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "question")]


class PatientProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_profile",
    )
    onboarding_completed = models.BooleanField(default=False)
    height = models.FloatField(
        null=True,
        blank=True,
        help_text="Height in centimeters",
    )
    weight = models.FloatField(
        null=True,
        blank=True,
        help_text="Current weight in kilograms",
    )
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    admin_notes = models.TextField(blank=True, help_text="Internal therapist notes about this patient")
    target_weight = models.FloatField(null=True, blank=True, help_text="Hedef kilo (kg)")
    target_waist = models.FloatField(null=True, blank=True, help_text="Hedef bel (cm)")
    target_hip = models.FloatField(null=True, blank=True, help_text="Hedef kalça (cm)")
    target_chest = models.FloatField(null=True, blank=True, help_text="Hedef göğüs (cm)")
    target_body_fat = models.FloatField(null=True, blank=True, help_text="Hedef yağ oranı (%)")
    daily_water_goal_ml = models.PositiveIntegerField(default=2000, help_text="Günlük su hedefi (ml)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patient Profile"
        verbose_name_plural = "Patient Profiles"

    def __str__(self):
        return f"Profile: {self.user.get_full_name() or self.user.username}"


class WeightHistory(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weight_history",
    )
    weight = models.FloatField(help_text="Weight in kilograms")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Weight History"
        verbose_name_plural = "Weight Histories"
        ordering = ["-recorded_at"]

    def __str__(self):
        return f"{self.patient.username}: {self.weight}kg @ {self.recorded_at:%Y-%m-%d}"


class BodyMeasurement(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="body_measurements",
    )
    date = models.DateField()
    label = models.CharField(max_length=80, blank=True, help_text="Ölçüm etiketi, örn. 'Başlangıç', 'Ara Ölçüm'")
    weight = models.FloatField(null=True, blank=True, help_text="Kilo (kg)")
    gogus = models.FloatField(null=True, blank=True, help_text="Göğüs (cm)")
    omuz = models.FloatField(null=True, blank=True, help_text="Omuz (cm)")
    bel = models.FloatField(null=True, blank=True, help_text="Bel (cm)")
    gobek = models.FloatField(null=True, blank=True, help_text="Göbek (cm)")
    alt_karin = models.FloatField(null=True, blank=True, help_text="Alt karın (cm)")
    kalca = models.FloatField(null=True, blank=True, help_text="Kalça (cm)")
    basen = models.FloatField(null=True, blank=True, help_text="Basen (cm)")
    sag_bacak = models.FloatField(null=True, blank=True, help_text="Sağ bacak (cm)")
    sol_bacak = models.FloatField(null=True, blank=True, help_text="Sol bacak (cm)")
    sag_kol = models.FloatField(null=True, blank=True, help_text="Sağ kol (cm)")
    sol_kol = models.FloatField(null=True, blank=True, help_text="Sol kol (cm)")
    yag_orani = models.FloatField(null=True, blank=True, help_text="Yağ oranı (%)")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vücut Ölçümü"
        verbose_name_plural = "Vücut Ölçümleri"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.patient.get_full_name()} — {self.date}"


class PatientProgressPhoto(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="progress_photos",
    )
    image = models.ImageField(upload_to=patient_photo_path)
    category = models.CharField(
        max_length=32,
        choices=PhotoCategory.choices,
        default=PhotoCategory.POSTURE_FRONT,
    )
    title = models.CharField(max_length=120, blank=True)
    note = models.TextField(blank=True)
    taken_at = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_patient_photos",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Patient Progress Photo"
        verbose_name_plural = "Patient Progress Photos"
        ordering = ["-taken_at", "-created_at"]

    def __str__(self):
        return f"{self.patient.username} — {self.get_category_display()} ({self.created_at:%Y-%m-%d})"


class SiteSettings(models.Model):
    """Tekil site/iletişim ayarları (adres, telefon, sosyal medya, analytics)."""

    # İletişim
    clinic_name = models.CharField(max_length=120, default="JFS Method")
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    working_hours = models.TextField(
        blank=True,
        help_text="Örn. Pazartesi–Cuma 09:00–18:00",
    )
    map_embed_url = models.URLField(
        max_length=600,
        blank=True,
        help_text="Google Haritalar 'embed' iframe src bağlantısı",
    )

    # Sosyal medya
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    x_url = models.URLField(blank=True, verbose_name="X (Twitter) URL")
    youtube_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)

    # SEO / Analytics
    google_analytics_id = models.CharField(
        max_length=40,
        blank=True,
        help_text="Örn. G-XXXXXXXXXX",
    )
    google_search_console_verification = models.CharField(
        max_length=120,
        blank=True,
        help_text="Search Console 'HTML etiketi' doğrulama içeriği (content değeri)",
    )

    registration_enabled = models.BooleanField(default=True)

    # Anasayfa bölüm görünürlükleri
    section_stats = models.BooleanField(default=True, verbose_name="İstatistik Şeridi")
    section_marquee = models.BooleanField(default=True, verbose_name="Marka Marquee")
    section_about = models.BooleanField(default=True, verbose_name="Hakkımızda")
    section_services = models.BooleanField(default=True, verbose_name="Hizmetler")
    section_digital_twin = models.BooleanField(default=True, verbose_name="Dijital İkiz")
    section_treatments = models.BooleanField(default=True, verbose_name="Tedavi Alanları")
    section_how_it_works = models.BooleanField(default=True, verbose_name="Nasıl Çalışır")
    section_why_us = models.BooleanField(default=True, verbose_name="Neden JFS")
    section_testimonials = models.BooleanField(default=True, verbose_name="Hasta Yorumları")
    section_packages = models.BooleanField(default=True, verbose_name="Paketler")
    section_cta = models.BooleanField(default=True, verbose_name="CTA Banner")
    section_faq = models.BooleanField(default=True, verbose_name="SSS")

    # Uzman profili
    expert_visible = models.BooleanField(
        default=True,
        help_text="Anasayfadaki uzman profil bölümünü göster/gizle",
    )
    expert_name = models.CharField(max_length=120, blank=True, default="Dr. Ayşe Yılmaz")
    expert_title = models.CharField(
        max_length=200, blank=True,
        default="Fizyoterapist & Ortopedik Rehabilitasyon Uzmanı",
    )
    expert_bio = models.TextField(
        blank=True,
        default="15 yıllık deneyimiyle dijital fizyoterapi alanında öncü. Kişiselleştirilmiş 3D tedavi planları ve veri odaklı rehabilitasyon yaklaşımıyla 2.000+ hastaya hizmet vermiştir.",
    )
    expert_years = models.PositiveSmallIntegerField(default=15, help_text="Yıl deneyim")
    expert_patient_count = models.CharField(max_length=20, blank=True, default="2.000+")
    expert_rating = models.CharField(max_length=10, blank=True, default="4.9")
    expert_badges = models.TextField(
        blank=True,
        default="Ortopedik Rehabilitasyon,Spor Yaralanmaları,3D Postür Analizi,Manuel Terapi",
        help_text="Virgülle ayrılmış uzmanlık etiketleri",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site Ayarları"
        verbose_name_plural = "Site Ayarları"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Site Ayarları"


class PostureAssessment(models.Model):
    """Foto tabanlı postür analizi sonucu (poz açıları + işaretlenmiş görsel)."""

    class View(models.TextChoices):
        FRONT = "front", "Önden"
        SIDE = "side", "Yandan"
        BACK = "back", "Arkadan"

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posture_assessments",
    )
    view = models.CharField(max_length=10, choices=View.choices, default=View.FRONT)
    image = models.ImageField(upload_to=posture_image_path)
    metrics = models.JSONField(default=dict, blank=True)
    summary = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_posture_assessments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Postür Analizi"
        verbose_name_plural = "Postür Analizleri"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient.username} — {self.get_view_display()} ({self.created_at:%Y-%m-%d})"


class PatientNotification(models.Model):
    """Hastanın uygulama içi bildirim geçmişi."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="patient_notifications",
    )
    notification_type = models.CharField(max_length=32, default="general")
    title = models.CharField(max_length=120)
    message = models.TextField()
    link = models.CharField(max_length=200, default="/hesabim")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.title}"


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=160, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "İletişim Mesajı"
        verbose_name_plural = "İletişim Mesajları"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject or 'Konu yok'} ({self.created_at:%Y-%m-%d})"


class Faq(models.Model):
    question = models.CharField(max_length=500)
    answer = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        verbose_name = "SSS"
        verbose_name_plural = "SSS"

    def __str__(self):
        return self.question[:80]


class DietItem(models.Model):
    """Tek bir yemek/besin kalemi (kütüphane)."""
    name = models.CharField(max_length=200)
    calories = models.PositiveIntegerField(help_text="kcal")
    protein = models.DecimalField(max_digits=6, decimal_places=1, default=0, help_text="gram")
    carbs = models.DecimalField(max_digits=6, decimal_places=1, default=0, help_text="gram")
    fat = models.DecimalField(max_digits=6, decimal_places=1, default=0, help_text="gram")
    portion = models.CharField(max_length=80, blank=True, help_text="örn: 1 kase, 200 g")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Besin"
        verbose_name_plural = "Besinler"

    def __str__(self):
        return f"{self.name} ({self.calories} kcal)"


class DietPlan(models.Model):
    """Bir öğrenciye atanan günlük diyet planı."""
    MEAL_CHOICES = [
        ("sabah", "Kahvaltı"),
        ("ara1", "Ara Öğün 1"),
        ("ogle", "Öğle"),
        ("ara2", "Ara Öğün 2"),
        ("aksam", "Akşam"),
        ("gece", "Gece"),
    ]
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="diet_plans",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="assigned_diet_plans",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField(help_text="Planın uygulanacağı tarih")
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES, default="ogle")
    items = models.ManyToManyField(DietItem, through="DietPlanItem", blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "meal_type"]
        verbose_name = "Diyet Planı"
        verbose_name_plural = "Diyet Planları"

    def __str__(self):
        return f"{self.patient.get_full_name()} — {self.title} ({self.date})"

    @property
    def total_calories(self):
        return sum(
            pi.diet_item.calories * pi.quantity for pi in self.plan_items.all()
        )


class DietPlanItem(models.Model):
    """Bir diyet planındaki belirli besin ve miktarı."""
    plan = models.ForeignKey(DietPlan, on_delete=models.CASCADE, related_name="plan_items")
    diet_item = models.ForeignKey(DietItem, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=5, decimal_places=2, default=1, help_text="Porsiyon çarpanı")
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Plan Besini"
        verbose_name_plural = "Plan Besinleri"


class DietProgram(models.Model):
    """Yeniden kullanılabilir global beslenme programı şablonu."""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="created_diet_programs"
    )
    title = models.CharField(max_length=200)
    goals = models.TextField(blank=True, help_text="Hedefler (her satır bir madde)")
    feeding_notes = models.CharField(max_length=300, blank=True, help_text="örn: 20.00 sonrası sadece su")
    duration_days = models.PositiveSmallIntegerField(default=7)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Beslenme Programı"
        verbose_name_plural = "Beslenme Programları"

    def __str__(self):
        return self.title


class PatientDietAssignment(models.Model):
    """Bir öğrenciye atanan beslenme programı."""
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="diet_assignments"
    )
    program = models.ForeignKey(DietProgram, on_delete=models.CASCADE, related_name="assignments")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="made_diet_assignments"
    )
    is_active = models.BooleanField(default=True)
    note = models.CharField(max_length=300, blank=True)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assigned_at"]
        unique_together = [("patient", "program")]
        verbose_name = "Öğrenci Beslenme Ataması"
        verbose_name_plural = "Öğrenci Beslenme Atamaları"

    def __str__(self):
        return f"{self.patient.get_full_name()} — {self.program.title}"


class DietDay(models.Model):
    """Program içindeki tek bir gün."""
    program = models.ForeignKey(DietProgram, on_delete=models.CASCADE, related_name="days")
    day_number = models.PositiveSmallIntegerField()
    label = models.CharField(max_length=50, blank=True, help_text="örn: Pazartesi, Gün 1")
    description = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["day_number"]
        unique_together = [("program", "day_number")]
        verbose_name = "Diyet Günü"
        verbose_name_plural = "Diyet Günleri"

    def __str__(self):
        return f"{self.program.title} — Gün {self.day_number}"


class DietMeal(models.Model):
    """Bir günün içindeki öğün."""
    MEAL_CHOICES = [
        ("sabah",  "Kahvaltı"),
        ("ara1",   "Ara Öğün 1"),
        ("ogle",   "Öğle"),
        ("ara2",   "Ara Öğün 2"),
        ("aksam",  "Akşam"),
        ("gece",   "Gece"),
        ("serbest","Serbest Öğün"),
    ]
    day = models.ForeignKey(DietDay, on_delete=models.CASCADE, related_name="meals")
    meal_type = models.CharField(max_length=10, choices=MEAL_CHOICES, default="ogle")
    meal_time = models.CharField(max_length=10, blank=True, help_text="örn: 12:00")
    description = models.CharField(max_length=300, blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "meal_type"]
        verbose_name = "Öğün"
        verbose_name_plural = "Öğünler"

    @property
    def total_calories(self):
        return sum(i.calories for i in self.items.all())


class DietMealItem(models.Model):
    """Öğün içindeki besin — kütüphaneden veya serbest metin."""
    meal = models.ForeignKey(DietMeal, on_delete=models.CASCADE, related_name="items")
    diet_item = models.ForeignKey(DietItem, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=200)
    quantity = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    calories = models.PositiveIntegerField(default=0)
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Öğün Besini"
        verbose_name_plural = "Öğün Besinleri"

    def __str__(self):
        return self.name


class AttendanceRecord(models.Model):
    """Randevudan bağımsız günlük katılım kaydı."""
    STATUS_CHOICES = [("came", "Geldi"), ("no_show", "Gelmedi")]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    session_package = models.ForeignKey(
        "SessionPackage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="marked_attendances",
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("patient", "date")]
        ordering = ["-date"]
        verbose_name = "Katılım Kaydı"
        verbose_name_plural = "Katılım Kayıtları"

    def __str__(self):
        return f"{self.patient.get_full_name()} — {self.date} — {self.get_status_display()}"


class Testimonial(models.Model):
    """Anasayfadaki hasta yorumları."""
    name = models.CharField(max_length=100)
    treatment = models.CharField(max_length=100, blank=True, help_text="Tedavi türü (örn. Bel Ağrısı)")
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, choices=[(i, f"{i} Yıldız") for i in range(1, 6)])
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "created_at"]
        verbose_name = "Hasta Yorumu"
        verbose_name_plural = "Hasta Yorumları"

    def __str__(self):
        return f"{self.name} — {self.rating}★"


class LandingService(models.Model):
    """Anasayfa Hizmetler bölümü kartları."""
    icon = models.CharField(max_length=10, default="🎯", help_text="Emoji ikon")
    tag = models.CharField(max_length=40, blank=True, help_text="Kart etiketi (örn. Bireysel)")
    title = models.CharField(max_length=120)
    description = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Hizmet"
        verbose_name_plural = "Hizmetler"

    def __str__(self):
        return self.title


class LandingTreatment(models.Model):
    """Anasayfa Tedavi Alanları bölümü kartları."""
    title = models.CharField(max_length=120)
    description = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Tedavi Alanı"
        verbose_name_plural = "Tedavi Alanları"

    def __str__(self):
        return self.title


class LandingWhyUsItem(models.Model):
    """Anasayfa Neden JFS bölümü öne çıkan maddeler."""
    icon = models.CharField(max_length=10, default="✅", help_text="Emoji ikon")
    title = models.CharField(max_length=120)
    description = models.TextField()
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        verbose_name = "Neden JFS Maddesi"
        verbose_name_plural = "Neden JFS Maddeleri"

    def __str__(self):
        return self.title
