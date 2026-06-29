from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaff

from .models import Exercise, ExerciseAssignment
from .serializers import (
    ExerciseAssignSerializer,
    ExerciseAssignmentSerializer,
    ExerciseSerializer,
    ExerciseWriteSerializer,
)


class AdminExerciseListView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        # Kütüphane yönetimi için tüm egzersizler (aktif + pasif) döner.
        exercises = Exercise.objects.all().order_by("title")
        return Response(
            ExerciseSerializer(
                exercises, many=True, context={"request": request}
            ).data
        )

    def post(self, request):
        serializer = ExerciseWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exercise = serializer.save()
        return Response(
            ExerciseSerializer(exercise, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminExerciseDetailView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, exercise_id):
        try:
            return Exercise.objects.get(pk=exercise_id)
        except Exercise.DoesNotExist:
            return None

    def patch(self, request, exercise_id):
        exercise = self.get_object(exercise_id)
        if not exercise:
            return Response({"detail": "Egzersiz bulunamadı."}, status=404)

        serializer = ExerciseWriteSerializer(
            exercise, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        exercise = serializer.save()
        return Response(
            ExerciseSerializer(exercise, context={"request": request}).data
        )

    def delete(self, request, exercise_id):
        exercise = self.get_object(exercise_id)
        if not exercise:
            return Response({"detail": "Egzersiz bulunamadı."}, status=404)

        # Atanmışsa silmek yerine pasifleştir (veri bütünlüğü).
        if exercise.assignments.exists():
            exercise.is_active = False
            exercise.save(update_fields=["is_active"])
            return Response(
                ExerciseSerializer(exercise, context={"request": request}).data
            )

        if exercise.image:
            exercise.image.delete(save=False)
        exercise.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPatientExerciseListCreateView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        try:
            patient = User.objects.get(pk=pk, is_staff=False)
        except User.DoesNotExist:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        assignments = (
            ExerciseAssignment.objects.filter(patient=patient)
            .select_related("exercise", "assigned_by")
            .prefetch_related("completions")
        )
        return Response(
            ExerciseAssignmentSerializer(
                assignments, many=True, context={"request": request}
            ).data
        )

    def post(self, request, pk):
        try:
            patient = User.objects.get(pk=pk, is_staff=False)
        except User.DoesNotExist:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        serializer = ExerciseAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            exercise = Exercise.objects.get(pk=data["exercise_id"], is_active=True)
        except Exercise.DoesNotExist:
            return Response({"detail": "Egzersiz bulunamadı."}, status=404)

        assignment = ExerciseAssignment.objects.create(
            patient=patient,
            exercise=exercise,
            assigned_by=request.user,
            therapist_note=data.get("therapist_note", ""),
            frequency=data.get("frequency", "daily"),
        )

        try:
            from accounts.push_service import send_push_to_users

            send_push_to_users(
                patient,
                title="Yeni ev egzersizi",
                body=f"Terapistiniz '{exercise.title}' egzersizini programınıza ekledi.",
                data={
                    "link": "/hesabim/egzersizlerim",
                    "notification_type": "exercise",
                },
            )
        except Exception:
            pass

        return Response(
            ExerciseAssignmentSerializer(
                assignment, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class AdminPatientExerciseDeactivateView(APIView):
    permission_classes = [IsStaff]

    def patch(self, request, pk, assignment_id):
        try:
            assignment = ExerciseAssignment.objects.get(
                pk=assignment_id, patient_id=pk
            )
        except ExerciseAssignment.DoesNotExist:
            return Response({"detail": "Atama bulunamadı."}, status=404)

        assignment.is_active = False
        assignment.save(update_fields=["is_active"])
        return Response(
            ExerciseAssignmentSerializer(
                assignment, context={"request": request}
            ).data
        )
