from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaff

from rest_framework import serializers as drf_serializers

from .models import Category, CategoryType, Exercise, ExerciseAssignment, NotificationSchedule, DailyWaterLog, DailyStepLog, ExerciseCompletion
from .serializers import (
    ExerciseAssignSerializer,
    ExerciseAssignmentSerializer,
    ExerciseSerializer,
    ExerciseWriteSerializer,
)


class NotificationScheduleSerializer(drf_serializers.ModelSerializer):
    notification_type_label = drf_serializers.CharField(
        source="get_notification_type_display", read_only=True
    )

    class Meta:
        model = NotificationSchedule
        fields = [
            "id",
            "notification_type",
            "notification_type_label",
            "title",
            "message",
            "send_times",
            "days_of_week",
            "is_enabled",
            "last_triggered_times",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_triggered_times", "created_at", "updated_at"]


class NotificationScheduleListCreateView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        schedules = NotificationSchedule.objects.all()
        return Response(NotificationScheduleSerializer(schedules, many=True).data)

    def post(self, request):
        serializer = NotificationScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        return Response(
            NotificationScheduleSerializer(schedule).data,
            status=status.HTTP_201_CREATED,
        )


class NotificationScheduleDetailView(APIView):
    permission_classes = [IsStaff]

    def get_object(self, pk):
        try:
            return NotificationSchedule.objects.get(pk=pk)
        except NotificationSchedule.DoesNotExist:
            return None

    def patch(self, request, pk):
        schedule = self.get_object(pk)
        if not schedule:
            return Response({"detail": "Bulunamadı."}, status=404)
        serializer = NotificationScheduleSerializer(schedule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save()
        return Response(NotificationScheduleSerializer(schedule).data)

    def delete(self, request, pk):
        schedule = self.get_object(pk)
        if not schedule:
            return Response({"detail": "Bulunamadı."}, status=404)
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FCMDeviceDebugView(APIView):
    """Kayıtlı FCM cihazlarını listeler."""
    permission_classes = [IsStaff]

    def get(self, request):
        from accounts.models import FCMDevice
        devices = FCMDevice.objects.select_related("user").order_by("-id")
        return Response({
            "total": devices.count(),
            "active": devices.filter(is_active=True).count(),
            "devices": [
                {
                    "id": d.id,
                    "user": d.user.username,
                    "is_staff": d.user.is_staff,
                    "is_active": d.is_active,
                    "token_preview": d.token[:20] + "...",
                }
                for d in devices[:50]
            ],
        })


class NotificationScheduleTestView(APIView):
    """Schedule'ı zaman ve saat kontrolü olmadan anında gönderir (test)."""
    permission_classes = [IsStaff]

    def post(self, request, pk):
        try:
            schedule = NotificationSchedule.objects.get(pk=pk)
        except NotificationSchedule.DoesNotExist:
            return Response({"detail": "Bulunamadı."}, status=404)

        from wellness.management.commands.fire_scheduled_notifications import (
            _get_target_users, LINK_MAP
        )
        from accounts.push_service import send_push_to_users

        users = _get_target_users(schedule.notification_type)
        link = LINK_MAP.get(schedule.notification_type, "/hesabim")

        if not users:
            return Response({"detail": "Hedef kullanıcı bulunamadı (kimse şartı karşılamıyor)."})

        send_push_to_users(
            users,
            title=schedule.title,
            body=schedule.message,
            data={"link": link, "notification_type": schedule.notification_type},
        )
        return Response({"detail": f"Test bildirimi gönderildi → {len(users)} kullanıcı."})


class AdminExerciseListView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        exercises = Exercise.objects.all().order_by("title")
        cat_id = request.query_params.get("category")
        if cat_id == "none":
            exercises = exercises.filter(category__isnull=True)
        elif cat_id:
            exercises = exercises.filter(category_id=cat_id)
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


class AdminPatientWellnessHistoryView(APIView):
    """Son 14 günlük su, adım ve egzersiz tamamlama geçmişi."""
    permission_classes = [IsStaff]

    def get(self, request, pk):
        from django.contrib.auth.models import User
        from django.utils import timezone
        import datetime

        patient = User.objects.filter(pk=pk, is_staff=False).first()
        if not patient:
            return Response({"detail": "Bulunamadı."}, status=404)

        today = timezone.localdate()
        days = int(request.query_params.get("days", 14))
        dates = [today - datetime.timedelta(days=i) for i in range(days - 1, -1, -1)]

        water_qs = {
            w.date: w.ml_consumed
            for w in DailyWaterLog.objects.filter(patient=patient, date__gte=dates[0])
        }
        step_qs = {
            s.date: s.step_count
            for s in DailyStepLog.objects.filter(patient=patient, date__gte=dates[0])
        }

        from django.db.models import Count as DCount
        completion_qs = {
            row["date"]: row["cnt"]
            for row in ExerciseCompletion.objects.filter(
                patient=patient, completed_at__date__gte=dates[0]
            ).values("date").annotate(cnt=DCount("id")).values("date", "cnt")
        } if hasattr(ExerciseCompletion, "date") else {}

        # ExerciseCompletion date field may not exist; use completed_at__date
        from django.db.models.functions import TruncDate
        completion_by_day = {}
        for row in (
            ExerciseCompletion.objects
            .filter(patient=patient, completed_at__date__gte=dates[0])
            .annotate(day=TruncDate("completed_at"))
            .values("day")
            .annotate(cnt=DCount("id"))
        ):
            completion_by_day[row["day"]] = row["cnt"]

        history = [
            {
                "date": d.isoformat(),
                "water_ml": water_qs.get(d, 0),
                "steps": step_qs.get(d, 0),
                "exercises_done": completion_by_day.get(d, 0),
            }
            for d in dates
        ]

        return Response({"history": history})


# ─── Category ────────────────────────────────────────────────────────────────

def _build_tree(categories, parent_id=None):
    result = []
    for cat in categories:
        pid = cat.parent_id
        if pid == parent_id:
            node = {
                "id": cat.id,
                "name": cat.name,
                "category_type": cat.category_type,
                "sort_order": cat.sort_order,
                "is_active": cat.is_active,
                "parent": pid,
                "children": _build_tree(categories, parent_id=cat.id),
            }
            result.append(node)
    return result


class AdminCategoryTreeView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        cat_type = request.query_params.get("type")
        qs = Category.objects.all()
        if cat_type:
            qs = qs.filter(category_type=cat_type)
        cats = list(qs)
        return Response(_build_tree(cats))

    def post(self, request):
        data = request.data
        name = (data.get("name") or "").strip()
        if not name:
            return Response({"error": "name zorunlu"}, status=400)
        cat_type = data.get("category_type")
        if cat_type not in (CategoryType.EXERCISE, CategoryType.DIET):
            return Response({"error": "category_type geçersiz"}, status=400)
        parent_id = data.get("parent") or None
        parent = None
        if parent_id:
            try:
                parent = Category.objects.get(pk=parent_id)
            except Category.DoesNotExist:
                return Response({"error": "parent bulunamadı"}, status=404)
        cat = Category.objects.create(
            name=name,
            category_type=cat_type,
            parent=parent,
            sort_order=data.get("sort_order", 0),
        )
        return Response({"id": cat.id, "name": cat.name, "category_type": cat.category_type, "parent": cat.parent_id, "sort_order": cat.sort_order, "is_active": cat.is_active, "children": []}, status=201)


class AdminCategoryDetailView(APIView):
    permission_classes = [IsStaff]

    def _get(self, pk):
        try:
            return Category.objects.get(pk=pk)
        except Category.DoesNotExist:
            return None

    def patch(self, request, pk):
        cat = self._get(pk)
        if not cat:
            return Response(status=404)
        data = request.data
        if "name" in data:
            cat.name = data["name"].strip()
        if "sort_order" in data:
            cat.sort_order = data["sort_order"]
        if "is_active" in data:
            cat.is_active = data["is_active"]
        if "parent" in data:
            parent_id = data["parent"]
            cat.parent_id = parent_id
        cat.save()
        return Response({"id": cat.id, "name": cat.name, "category_type": cat.category_type, "parent": cat.parent_id, "sort_order": cat.sort_order, "is_active": cat.is_active})

    def delete(self, request, pk):
        cat = self._get(pk)
        if not cat:
            return Response(status=404)
        cat.delete()
        return Response(status=204)
