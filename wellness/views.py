from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import PatientProgressPhoto
from accounts.admin_serializers import PatientProgressPhotoSerializer
from accounts.models import WeightHistory

from .models import DailyStepLog, DailyWaterLog, ExerciseAssignment, ExerciseCompletion, RegionPainLog
from .serializers import (
    CompleteExerciseSerializer,
    ExerciseAssignmentSerializer,
    ExerciseCompletionSerializer,
    PainMapUpdateSerializer,
    RegionPainLogSerializer,
    WellnessDashboardSerializer,
    build_wellness_stats,
    latest_pain_per_region,
)


class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and not request.user.is_staff
        )


class WellnessDashboardView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        user = request.user
        pain_map = latest_pain_per_region(user)
        exercises = (
            ExerciseAssignment.objects.filter(patient=user, is_active=True)
            .select_related("exercise", "assigned_by")
            .prefetch_related("completions")
        )
        photos = PatientProgressPhoto.objects.filter(patient=user).select_related(
            "uploaded_by"
        )[:12]
        weight_history = WeightHistory.objects.filter(patient=user).order_by(
            "recorded_at"
        )[:30]

        data = {
            "pain_map": RegionPainLogSerializer(pain_map, many=True).data,
            "exercises": ExerciseAssignmentSerializer(
                exercises, many=True, context={"request": request}
            ).data,
            "weight_history": [
                {
                    "weight": entry.weight,
                    "recorded_at": entry.recorded_at.isoformat(),
                }
                for entry in weight_history
            ],
            "progress_photos": PatientProgressPhotoSerializer(
                photos, many=True, context={"request": request}
            ).data,
            "stats": build_wellness_stats(user),
        }
        serializer = WellnessDashboardSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)


class PainMapView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        logs = latest_pain_per_region(request.user)
        return Response(RegionPainLogSerializer(logs, many=True).data)

    def post(self, request):
        serializer = PainMapUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created = []
        for entry in serializer.validated_data["entries"]:
            log = RegionPainLog.objects.create(
                patient=request.user,
                region=entry["region"],
                pain_level=entry["pain_level"],
                note=entry.get("note", ""),
            )
            created.append(log)

        return Response(
            RegionPainLogSerializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class PatientExerciseListView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        assignments = (
            ExerciseAssignment.objects.filter(patient=request.user, is_active=True)
            .select_related("exercise", "assigned_by")
            .prefetch_related("completions")
        )
        return Response(
            ExerciseAssignmentSerializer(
                assignments, many=True, context={"request": request}
            ).data
        )


class CompleteExerciseView(APIView):
    permission_classes = [IsPatient]

    def post(self, request, pk):
        try:
            assignment = ExerciseAssignment.objects.select_related("exercise").get(
                pk=pk,
                patient=request.user,
                is_active=True,
            )
        except ExerciseAssignment.DoesNotExist:
            return Response(
                {"detail": "Egzersiz ataması bulunamadı."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompleteExerciseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        completion = ExerciseCompletion.objects.create(
            assignment=assignment,
            patient=request.user,
            **serializer.validated_data,
        )

        return Response(
            ExerciseCompletionSerializer(completion).data,
            status=status.HTTP_201_CREATED,
        )


class PatientProgressPhotoListView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        photos = PatientProgressPhoto.objects.filter(patient=request.user).select_related(
            "uploaded_by"
        )
        return Response(
            PatientProgressPhotoSerializer(
                photos, many=True, context={"request": request}
            ).data
        )

    def post(self, request):
        from accounts.admin_serializers import PatientProgressPhotoUploadSerializer
        serializer = PatientProgressPhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = serializer.save(patient=request.user, uploaded_by=request.user)
        return Response(
            PatientProgressPhotoSerializer(photo, context={"request": request}).data,
            status=201,
        )


class PatientProgressPhotoDeleteView(APIView):
    permission_classes = [IsPatient]

    def delete(self, request, pk):
        try:
            photo = PatientProgressPhoto.objects.get(pk=pk, patient=request.user)
        except PatientProgressPhoto.DoesNotExist:
            return Response(status=404)
        if photo.image:
            photo.image.delete(save=False)
        photo.delete()
        return Response(status=204)


class DailyWaterView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        from django.utils import timezone
        today = timezone.localdate()
        log, _ = DailyWaterLog.objects.get_or_create(patient=request.user, date=today)
        return Response({"date": str(today), "ml_consumed": log.ml_consumed})

    def post(self, request):
        from django.utils import timezone
        today = timezone.localdate()
        ml = request.data.get("ml_consumed", 0)
        try:
            ml = int(ml)
        except (ValueError, TypeError):
            return Response({"detail": "Geçersiz değer."}, status=status.HTTP_400_BAD_REQUEST)
        log, _ = DailyWaterLog.objects.get_or_create(patient=request.user, date=today)
        log.ml_consumed = max(0, ml)
        log.save(update_fields=["ml_consumed"])
        return Response({"date": str(today), "ml_consumed": log.ml_consumed})


class DailyStepView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        from django.utils import timezone
        today = timezone.localdate()
        log, _ = DailyStepLog.objects.get_or_create(patient=request.user, date=today)
        return Response({"date": str(today), "step_count": log.step_count})

    def post(self, request):
        from django.utils import timezone
        today = timezone.localdate()
        steps = request.data.get("step_count", 0)
        try:
            steps = int(steps)
        except (ValueError, TypeError):
            return Response({"detail": "Geçersiz değer."}, status=status.HTTP_400_BAD_REQUEST)
        log, _ = DailyStepLog.objects.get_or_create(patient=request.user, date=today)
        log.step_count = max(0, steps)
        log.save(update_fields=["step_count"])
        return Response({"date": str(today), "step_count": log.step_count})


# ── Meal Log ──────────────────────────────────────────────────────────────────

from rest_framework import serializers as drf_serializers
from rest_framework.parsers import MultiPartParser, FormParser


class MealLogSerializer(drf_serializers.ModelSerializer):
    photo_url = drf_serializers.SerializerMethodField()
    meal_type_label = drf_serializers.CharField(source="get_meal_type_display", read_only=True)

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if obj.photo and request:
            return request.build_absolute_uri(obj.photo.url)
        return None

    class Meta:
        from wellness.models import MealLog
        model = MealLog
        fields = ["id", "meal_type", "meal_type_label", "description", "photo_url", "logged_at", "admin_note", "admin_note_at", "created_at"]
        read_only_fields = ["admin_note", "admin_note_at", "created_at"]


class PatientMealLogListView(APIView):
    permission_classes = [IsPatient]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        from .models import MealLog
        from django.utils.dateparse import parse_date
        qs = MealLog.objects.filter(user=request.user)
        date_str = request.query_params.get("date")
        if date_str:
            d = parse_date(date_str)
            if d:
                qs = qs.filter(logged_at__date=d)
        return Response(MealLogSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request):
        from .models import MealLog
        import django.utils.timezone as tz
        data = {
            "meal_type": request.data.get("meal_type"),
            "description": request.data.get("description", ""),
            "logged_at": request.data.get("logged_at") or tz.now().isoformat(),
        }
        s = MealLogSerializer(data=data, context={"request": request})
        s.is_valid(raise_exception=True)
        log = s.save(user=request.user)
        if "photo" in request.FILES:
            log.photo = request.FILES["photo"]
            log.save(update_fields=["photo"])
        return Response(MealLogSerializer(log, context={"request": request}).data, status=201)


class PatientMealLogDetailView(APIView):
    permission_classes = [IsPatient]

    def delete(self, request, pk):
        from .models import MealLog
        try:
            log = MealLog.objects.get(pk=pk, user=request.user)
        except MealLog.DoesNotExist:
            return Response(status=404)
        log.delete()
        return Response(status=204)


# ── Program (package-based) ───────────────────────────────────────────────────

class PatientProgramView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        """Kullanıcının aktif paketindeki egzersiz programını döner."""
        from .models import UserPackageAssignment, ProgramExerciseLog
        from django.utils.timezone import localdate

        assignment = (
            UserPackageAssignment.objects.filter(user=request.user, is_active=True)
            .select_related("package__exercise_program__category")
            .prefetch_related("package__exercise_program__days__items__exercise")
            .first()
        )

        if not assignment or not assignment.package.exercise_program:
            return Response({"program": None})

        program = assignment.package.exercise_program
        today = localdate()

        # Bugün tamamlanan item id'leri
        completed_today = set(
            ProgramExerciseLog.objects.filter(
                user=request.user,
                completed_at__date=today,
                program_item__day__program=program,
            ).values_list("program_item_id", flat=True)
        )

        days_data = []
        for day in program.days.all():
            items_data = []
            for item in day.items.all():
                items_data.append({
                    "id": item.id,
                    "exercise_id": item.exercise_id,
                    "exercise_title": item.exercise.title,
                    "exercise_image": request.build_absolute_uri(item.exercise.image.url) if item.exercise.image else None,
                    "sets": item.sets,
                    "reps": item.reps,
                    "duration_seconds": item.duration_seconds,
                    "rest_seconds": item.rest_seconds,
                    "note": item.note,
                    "completed_today": item.id in completed_today,
                })
            days_data.append({
                "id": day.id,
                "day_number": day.day_number,
                "title": day.title,
                "items": items_data,
            })

        return Response({
            "program": {
                "id": program.id,
                "name": program.name,
                "description": program.description,
                "program_type": program.program_type,
                "difficulty": program.difficulty,
                "duration_weeks": program.duration_weeks,
                "days": days_data,
            }
        })


class PatientLogExerciseView(APIView):
    permission_classes = [IsPatient]

    def post(self, request, item_id):
        from .models import ExerciseProgramItem, ProgramExerciseLog

        try:
            item = ExerciseProgramItem.objects.select_related("day__program").get(pk=item_id)
        except ExerciseProgramItem.DoesNotExist:
            return Response(status=404)

        # Kullanıcının bu programa erişimi var mı?
        from .models import UserPackageAssignment
        has_access = UserPackageAssignment.objects.filter(
            user=request.user,
            is_active=True,
            package__exercise_program=item.day.program,
        ).exists()
        if not has_access:
            return Response({"detail": "Erişim yok."}, status=403)

        log, _ = ProgramExerciseLog.objects.get_or_create(
            user=request.user,
            program_item=item,
            completed_at__date=timezone.localdate(),
            defaults={
                "cycle": request.data.get("cycle", 1),
                "note": request.data.get("note", ""),
                "difficulty_felt": request.data.get("difficulty_felt"),
            },
        )
        return Response({"id": log.id, "completed_at": log.completed_at}, status=201)
