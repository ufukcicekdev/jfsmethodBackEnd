from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import PatientProgressPhoto
from accounts.admin_serializers import PatientProgressPhotoSerializer
from accounts.models import WeightHistory

from .models import ExerciseAssignment, ExerciseCompletion, RegionPainLog
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
