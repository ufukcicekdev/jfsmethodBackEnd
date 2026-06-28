from django.contrib.auth.models import User
from rest_framework import serializers

from appointments.models import Appointment

from .models import (
    AttendanceRecord,
    BodyMeasurement,
    DietItem,
    DietPlan,
    DietPlanItem,
    Faq,
    PackagePlan,
    PatientProfile,
    PatientProgressPhoto,
    PostureAssessment,
    SessionPackage,
    WeightHistory,
)


class PackagePlanSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, obj):
        if obj.image:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    class Meta:
        model = PackagePlan
        fields = [
            "id",
            "name",
            "total_sessions",
            "price",
            "description",
            "image",
            "image_url",
            "is_active",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "image_url"]

    def validate_total_sessions(self, value):
        if value < 1:
            raise serializers.ValidationError("Seans sayısı en az 1 olmalıdır.")
        return value


class SessionPackageSerializer(serializers.ModelSerializer):
    used_sessions = serializers.IntegerField(read_only=True)
    no_show_count = serializers.IntegerField(read_only=True)
    scheduled_count = serializers.IntegerField(read_only=True)
    remaining_sessions = serializers.IntegerField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    plan_name = serializers.SerializerMethodField()

    class Meta:
        model = SessionPackage
        fields = [
            "id",
            "plan",
            "plan_name",
            "name",
            "total_sessions",
            "price",
            "is_paid",
            "paid_at",
            "purchased_at",
            "note",
            "is_active",
            "used_sessions",
            "no_show_count",
            "scheduled_count",
            "remaining_sessions",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "is_active", "created_at"]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        return obj.created_by.get_full_name() or obj.created_by.username

    def get_plan_name(self, obj):
        return obj.plan.name if obj.plan else None


class SessionPackageCreateSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    total_sessions = serializers.IntegerField(required=False, min_value=1)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    purchased_at = serializers.DateField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)
    is_paid = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("plan_id") and not attrs.get("total_sessions"):
            raise serializers.ValidationError(
                "Bir paket planı seçin veya seans sayısını girin."
            )
        return attrs

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


class AdminPatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = ["height", "weight", "date_of_birth", "phone", "updated_at"]


class AdminPatientListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    height = serializers.SerializerMethodField()
    weight = serializers.SerializerMethodField()
    bmi = serializers.SerializerMethodField()
    remaining_sessions = serializers.SerializerMethodField()
    came_count = serializers.SerializerMethodField()
    no_show_count = serializers.SerializerMethodField()
    last_attended = serializers.SerializerMethodField()
    today_attendance = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "height",
            "weight",
            "bmi",
            "remaining_sessions",
            "came_count",
            "no_show_count",
            "last_attended",
            "today_attendance",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def _profile(self, obj):
        return getattr(obj, "patient_profile", None)

    def get_height(self, obj):
        profile = self._profile(obj)
        return profile.height if profile else None

    def get_weight(self, obj):
        profile = self._profile(obj)
        return profile.weight if profile else None

    def get_bmi(self, obj):
        profile = self._profile(obj)
        if not profile or not profile.height or not profile.weight:
            return None
        height_m = profile.height / 100
        return round(profile.weight / (height_m * height_m), 1)

    def get_remaining_sessions(self, obj):
        pkgs = SessionPackage.objects.filter(patient=obj, is_active=True)
        return sum(p.remaining_sessions for p in pkgs)

    def get_came_count(self, obj):
        return AttendanceRecord.objects.filter(patient=obj, status="came").count()

    def get_no_show_count(self, obj):
        return AttendanceRecord.objects.filter(patient=obj, status="no_show").count()

    def get_last_attended(self, obj):
        rec = AttendanceRecord.objects.filter(patient=obj, status="came").order_by("-date").first()
        return rec.date.isoformat() if rec else None

    def get_today_attendance(self, obj):
        from django.utils import timezone
        today = timezone.localdate()
        rec = AttendanceRecord.objects.filter(patient=obj, date=today).first()
        if not rec:
            return None
        return {"id": rec.id, "status": rec.status}


class AdminPatientDetailSerializer(AdminPatientListSerializer):
    phone = serializers.SerializerMethodField()
    date_of_birth = serializers.SerializerMethodField()
    admin_notes = serializers.SerializerMethodField()
    weight_history = serializers.SerializerMethodField()
    weight_stats = serializers.SerializerMethodField()
    progress_photos = serializers.SerializerMethodField()
    packages = serializers.SerializerMethodField()
    attendance = serializers.SerializerMethodField()

    class Meta(AdminPatientListSerializer.Meta):
        fields = AdminPatientListSerializer.Meta.fields + [
            "phone",
            "date_of_birth",
            "admin_notes",
            "weight_history",
            "weight_stats",
            "progress_photos",
            "packages",
            "attendance",
        ]

    def get_packages(self, obj):
        packages = SessionPackage.objects.filter(patient=obj).select_related(
            "created_by"
        )
        return SessionPackageSerializer(packages, many=True).data

    def get_attendance(self, obj):
        from django.utils import timezone

        now = timezone.now()
        appts = (
            Appointment.objects.filter(patient=obj)
            .select_related("doctor")
            .order_by("-appointment_datetime")
        )
        completed = appts.filter(status="completed").count()
        no_show = appts.filter(status="no_show").count()
        cancelled = appts.filter(status="cancelled").count()
        upcoming = appts.filter(
            status__in=["pending", "approved"],
            appointment_datetime__gte=now,
        ).count()

        history = [
            {
                "id": a.id,
                "appointment_datetime": a.appointment_datetime.isoformat(),
                "status": a.status,
                "doctor_name": a.doctor.get_full_name() or a.doctor.username,
            }
            for a in appts[:60]
        ]

        return {
            "completed": completed,
            "no_show": no_show,
            "cancelled": cancelled,
            "upcoming": upcoming,
            "history": history,
        }

    def get_phone(self, obj):
        profile = self._profile(obj)
        return profile.phone if profile else ""

    def get_admin_notes(self, obj):
        profile = self._profile(obj)
        return profile.admin_notes if profile else ""

    def get_date_of_birth(self, obj):
        profile = self._profile(obj)
        return profile.date_of_birth.isoformat() if profile and profile.date_of_birth else None

    def get_weight_history(self, obj):
        history = WeightHistory.objects.filter(patient=obj).order_by("-recorded_at")[:50]
        return WeightHistorySerializer(history, many=True).data

    def get_weight_stats(self, obj):
        from .weight_stats import get_weight_stats

        return get_weight_stats(obj.id)

    def get_progress_photos(self, obj):
        photos = PatientProgressPhoto.objects.filter(patient=obj).select_related(
            "uploaded_by"
        )
        return PatientProgressPhotoSerializer(
            photos, many=True, context=self.context
        ).data


class PatientProgressPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientProgressPhoto
        fields = [
            "id",
            "image_url",
            "category",
            "category_label",
            "title",
            "note",
            "taken_at",
            "uploaded_by_name",
            "created_at",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return None
        return obj.uploaded_by.get_full_name() or obj.uploaded_by.username


class PatientProgressPhotoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProgressPhoto
        fields = ["image", "category", "title", "note", "taken_at"]

    def validate_image(self, value):
        if value.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("Dosya boyutu en fazla 5 MB olabilir.")
        ext = value.name.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                "Yalnızca JPG, PNG veya WebP dosyaları yüklenebilir."
            )
        return value


class AdminPatientUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    height = serializers.FloatField(required=False, allow_null=True)
    weight = serializers.FloatField(required=False, allow_null=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    admin_notes = serializers.CharField(required=False, allow_blank=True)


class AdminPatientCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    password = serializers.CharField(
        required=False, allow_blank=True, min_length=6, max_length=128
    )


class AdminAppointmentCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    doctor = serializers.IntegerField()
    appointment_datetime = serializers.DateTimeField()
    note = serializers.CharField(required=False, allow_blank=True)


class PostureAssessmentSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    view_label = serializers.CharField(source="get_view_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PostureAssessment
        fields = [
            "id",
            "view",
            "view_label",
            "image_url",
            "metrics",
            "summary",
            "created_by_name",
            "created_at",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        full = obj.created_by.get_full_name().strip()
        return full or obj.created_by.username


class PostureAssessmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostureAssessment
        fields = ["image", "view", "metrics", "summary"]

    def validate_image(self, value):
        if value.size > MAX_IMAGE_SIZE:
            raise serializers.ValidationError("Dosya boyutu en fazla 5 MB olabilir.")
        ext = value.name.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise serializers.ValidationError(
                "Yalnızca JPG, PNG veya WebP dosyaları yüklenebilir."
            )
        return value


class AdminWeightEntrySerializer(serializers.Serializer):
    weight = serializers.FloatField(min_value=20, max_value=300)


class WeightHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightHistory
        fields = ["id", "weight", "recorded_at"]
        read_only_fields = ["id", "recorded_at"]


class BodyMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyMeasurement
        fields = [
            "id", "date", "label", "weight",
            "gogus", "omuz", "bel", "gobek", "alt_karin",
            "kalca", "basen", "sag_bacak", "sol_bacak",
            "sag_kol", "sol_kol", "yag_orani", "notes", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class AdminAppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    patient_id = serializers.IntegerField(source="patient.id", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient_id",
            "patient_name",
            "doctor",
            "doctor_name",
            "appointment_datetime",
            "status",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username


class AdminAppointmentStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            "pending",
            "approved",
            "postponed",
            "completed",
            "cancelled",
            "no_show",
        ]
    )
    note = serializers.CharField(required=False, allow_blank=True)


class FaqSerializer(serializers.ModelSerializer):
    class Meta:
        model = Faq
        fields = ["id", "question", "answer", "sort_order", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class DietItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietItem
        fields = ["id", "name", "calories", "protein", "carbs", "fat", "portion", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class DietPlanItemSerializer(serializers.ModelSerializer):
    diet_item = DietItemSerializer(read_only=True)
    diet_item_id = serializers.PrimaryKeyRelatedField(
        queryset=DietItem.objects.all(), source="diet_item", write_only=True
    )

    class Meta:
        model = DietPlanItem
        fields = ["id", "diet_item", "diet_item_id", "quantity", "note"]


class DietPlanSerializer(serializers.ModelSerializer):
    plan_items = DietPlanItemSerializer(many=True, read_only=True)
    total_calories = serializers.IntegerField(read_only=True)
    assigned_by_name = serializers.SerializerMethodField()
    meal_type_label = serializers.SerializerMethodField()

    class Meta:
        model = DietPlan
        fields = [
            "id", "patient", "title", "description", "date", "meal_type",
            "meal_type_label", "plan_items", "total_calories",
            "assigned_by_name", "is_active", "created_at",
        ]
        read_only_fields = ["id", "created_at", "total_calories"]

    def get_assigned_by_name(self, obj):
        if not obj.assigned_by:
            return None
        return obj.assigned_by.get_full_name() or obj.assigned_by.username

    def get_meal_type_label(self, obj):
        return dict(DietPlan.MEAL_CHOICES).get(obj.meal_type, obj.meal_type)
