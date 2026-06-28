from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.admin_serializers import PatientProgressPhotoSerializer
from accounts.models import PatientProgressPhoto, WeightHistory

from .models import (
    BodyRegion,
    Exercise,
    ExerciseAssignment,
    ExerciseCompletion,
    ExerciseDifficulty,
    ExerciseFrequency,
    RegionPainLog,
)


class ExerciseSerializer(serializers.ModelSerializer):
    target_region_label = serializers.CharField(
        source="get_target_region_display", read_only=True
    )
    difficulty_label = serializers.CharField(
        source="get_difficulty_display", read_only=True
    )
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Exercise
        fields = [
            "id",
            "title",
            "description",
            "image_url",
            "instructions",
            "target_region",
            "target_region_label",
            "duration_minutes",
            "sets",
            "reps",
            "difficulty",
            "difficulty_label",
            "is_active",
        ]

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url


class ExerciseWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            "title",
            "description",
            "image",
            "instructions",
            "target_region",
            "duration_minutes",
            "sets",
            "reps",
            "difficulty",
            "is_active",
        ]

    def validate_image(self, value):
        if value in (None, ""):
            return value
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Dosya boyutu en fazla 5 MB olabilir.")
        ext = value.name.rsplit(".", 1)[-1].lower()
        if ext not in {"jpg", "jpeg", "png", "webp"}:
            raise serializers.ValidationError(
                "Yalnızca JPG, PNG veya WebP dosyaları yüklenebilir."
            )
        return value


class RegionPainLogSerializer(serializers.ModelSerializer):
    region_label = serializers.CharField(source="get_region_display", read_only=True)

    class Meta:
        model = RegionPainLog
        fields = [
            "id",
            "region",
            "region_label",
            "pain_level",
            "note",
            "recorded_at",
        ]
        read_only_fields = ["id", "recorded_at"]


class PainMapEntrySerializer(serializers.Serializer):
    region = serializers.ChoiceField(choices=BodyRegion.choices)
    pain_level = serializers.IntegerField(min_value=0, max_value=10)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class PainMapUpdateSerializer(serializers.Serializer):
    entries = PainMapEntrySerializer(many=True, min_length=1)


class ExerciseCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExerciseCompletion
        fields = [
            "id",
            "pain_before",
            "pain_after",
            "note",
            "completed_at",
        ]
        read_only_fields = ["id", "completed_at"]


class ExerciseAssignmentSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)
    frequency_label = serializers.CharField(source="get_frequency_display", read_only=True)
    assigned_by_name = serializers.SerializerMethodField()
    completions_this_week = serializers.SerializerMethodField()
    last_completed_at = serializers.SerializerMethodField()
    completed_today = serializers.SerializerMethodField()

    class Meta:
        model = ExerciseAssignment
        fields = [
            "id",
            "exercise",
            "therapist_note",
            "frequency",
            "frequency_label",
            "is_active",
            "start_date",
            "end_date",
            "assigned_by_name",
            "completions_this_week",
            "last_completed_at",
            "completed_today",
            "created_at",
        ]

    def get_assigned_by_name(self, obj):
        if not obj.assigned_by:
            return None
        return obj.assigned_by.get_full_name() or obj.assigned_by.username

    def get_completions_this_week(self, obj):
        from django.utils import timezone
        from datetime import timedelta

        week_ago = timezone.now() - timedelta(days=7)
        return obj.completions.filter(completed_at__gte=week_ago).count()

    def get_last_completed_at(self, obj):
        last = obj.completions.order_by("-completed_at").first()
        return last.completed_at.isoformat() if last else None

    def get_completed_today(self, obj):
        from django.utils import timezone

        today = timezone.localdate()
        return obj.completions.filter(completed_at__date=today).exists()


class ExerciseAssignSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    therapist_note = serializers.CharField(required=False, allow_blank=True)
    frequency = serializers.ChoiceField(
        choices=ExerciseFrequency.choices,
        default=ExerciseFrequency.DAILY,
    )


class CompleteExerciseSerializer(serializers.Serializer):
    pain_before = serializers.IntegerField(
        required=False, min_value=0, max_value=10, allow_null=True
    )
    pain_after = serializers.IntegerField(
        required=False, min_value=0, max_value=10, allow_null=True
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class WellnessDashboardSerializer(serializers.Serializer):
    pain_map = RegionPainLogSerializer(many=True)
    exercises = ExerciseAssignmentSerializer(many=True)
    weight_history = serializers.ListField()
    progress_photos = PatientProgressPhotoSerializer(many=True)
    stats = serializers.DictField()


def build_wellness_stats(user):
    from django.db.models import Avg
    from django.utils import timezone
    from datetime import timedelta

    week_ago = timezone.now() - timedelta(days=7)
    two_weeks_ago = timezone.now() - timedelta(days=14)

    active_assignments = ExerciseAssignment.objects.filter(
        patient=user, is_active=True
    )
    completions_week = ExerciseCompletion.objects.filter(
        patient=user, completed_at__gte=week_ago
    ).count()

    latest_pain = (
        RegionPainLog.objects.filter(patient=user)
        .values("region")
        .annotate(avg_pain=Avg("pain_level"))
    )
    latest_avg = (
        sum(item["avg_pain"] for item in latest_pain) / len(latest_pain)
        if latest_pain
        else None
    )

    prev_pain = RegionPainLog.objects.filter(
        patient=user,
        recorded_at__gte=two_weeks_ago,
        recorded_at__lt=week_ago,
    ).aggregate(avg=Avg("pain_level"))["avg"]

    pain_change = None
    if latest_avg is not None and prev_pain is not None:
        pain_change = round(prev_pain - latest_avg, 1)

    weight_entries = WeightHistory.objects.filter(patient=user).order_by(
        "-recorded_at"
    )[:2]
    weight_change = None
    if len(weight_entries) >= 2:
        weight_change = round(
            weight_entries[0].weight - weight_entries[1].weight, 1
        )

    return {
        "active_exercises": active_assignments.count(),
        "completions_this_week": completions_week,
        "average_pain": round(latest_avg, 1) if latest_avg is not None else None,
        "pain_change_week": pain_change,
        "weight_change_recent": weight_change,
        "progress_photo_count": PatientProgressPhoto.objects.filter(
            patient=user
        ).count(),
    }


def latest_pain_per_region(user):
    logs = []
    for region_value, _ in BodyRegion.choices:
        entry = (
            RegionPainLog.objects.filter(patient=user, region=region_value)
            .order_by("-recorded_at")
            .first()
        )
        if entry:
            logs.append(entry)
    return logs
