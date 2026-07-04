from django.contrib.auth.models import User
from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment, AppointmentStatus

from .admin_serializers import (
    AdminAppointmentCreateSerializer,
    AdminAppointmentSerializer,
    AdminAppointmentStatusSerializer,
    AdminPatientCreateSerializer,
    AdminPatientDetailSerializer,
    AdminPatientListSerializer,
    AdminPatientUpdateSerializer,
    AdminWeightEntrySerializer,
    BodyMeasurementSerializer,
    DietItemSerializer,
    DietPlanSerializer,
    FaqSerializer,
    OnboardingAnswerSerializer,
    OnboardingQuestionSerializer,
    PackagePlanSerializer,
    PatientProgressPhotoSerializer,
    PatientProgressPhotoUploadSerializer,
    PostureAssessmentCreateSerializer,
    PostureAssessmentSerializer,
    SessionPackageCreateSerializer,
    SessionPackageSerializer,
    WeightHistorySerializer,
)
from .models import (
    AttendanceRecord,
    BodyMeasurement,
    DietItem,
    DietPlan,
    DietPlanItem,
    Faq,
    OnboardingAnswer,
    OnboardingQuestion,
    PackagePlan,
    PatientProfile,
    PatientProgressPhoto,
    PostureAssessment,
    SessionPackage,
    WeightHistory,
)
from .permissions import IsStaff


def patient_queryset():
    return (
        User.objects.filter(is_staff=False, is_superuser=False)
        .select_related("patient_profile")
        .order_by("-date_joined")
    )


class AdminDashboardView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        from datetime import timedelta
        from django.db.models import Count as DCount
        from wellness.models import ExerciseCompletion

        today = timezone.localdate()

        # Weekly attendance: last 8 weeks, distinct patients who completed at least 1 exercise
        weekly_attendance = []
        for i in range(7, -1, -1):
            week_start = today - timedelta(days=today.weekday() + 7 * i)
            week_end = week_start + timedelta(days=6)
            count = (
                ExerciseCompletion.objects.filter(
                    completed_at__date__gte=week_start,
                    completed_at__date__lte=week_end,
                )
                .values("patient")
                .distinct()
                .count()
            )
            weekly_attendance.append({
                "week_start": str(week_start),
                "count": count,
            })

        # Top 5 most completed exercises in last 30 days
        thirty_days_ago = today - timedelta(days=30)
        top_exercises = (
            ExerciseCompletion.objects.filter(
                completed_at__date__gte=thirty_days_ago,
            )
            .values("assignment__exercise__title")
            .annotate(total=DCount("id"))
            .order_by("-total")[:5]
        )
        top_exercises_data = [
            {"title": item["assignment__exercise__title"], "count": item["total"]}
            for item in top_exercises
        ]

        return Response(
            {
                "patient_count": User.objects.filter(
                    is_staff=False, is_superuser=False
                ).count(),
                "appointment_count": Appointment.objects.count(),
                "pending_appointments": Appointment.objects.filter(
                    status=AppointmentStatus.PENDING
                ).count(),
                "today_appointments": Appointment.objects.filter(
                    appointment_datetime__date=today,
                    status__in=[
                        AppointmentStatus.PENDING,
                        AppointmentStatus.APPROVED,
                    ],
                ).count(),
                "active_packages": SessionPackage.objects.filter(is_active=True).count(),
                "weekly_attendance": weekly_attendance,
                "top_exercises": top_exercises_data,
            }
        )


class AdminPatientListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        search = request.query_params.get("search", "").strip()
        queryset = patient_queryset()

        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        serializer = AdminPatientListSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AdminPatientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        email = (data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            return Response(
                {"detail": "Bu e-posta ile kayıtlı bir kullanıcı zaten var."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = self._generate_username(
            email, data["first_name"], data.get("last_name", "")
        )

        provided_password = (data.get("password") or "").strip()
        generated_password = ""
        if provided_password:
            password = provided_password
        else:
            from django.utils.crypto import get_random_string

            generated_password = get_random_string(10)
            password = generated_password

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=data["first_name"],
            last_name=data.get("last_name", ""),
        )

        profile, _ = PatientProfile.objects.get_or_create(user=user)
        phone = (data.get("phone") or "").strip()
        if phone:
            profile.phone = phone
            profile.save(update_fields=["phone", "updated_at"])

        patient = patient_queryset().get(pk=user.pk)
        return Response(
            {
                "patient": AdminPatientDetailSerializer(
                    patient, context={"request": request}
                ).data,
                "username": username,
                "generated_password": generated_password,
            },
            status=status.HTTP_201_CREATED,
        )

    def _generate_username(self, email, first_name, last_name):
        import re

        if email:
            base = email.split("@")[0]
        else:
            base = f"{first_name}{last_name}".strip() or "ogrenci"
        base = re.sub(r"[^a-zA-Z0-9_.]", "", base.lower()) or "ogrenci"

        username = base
        counter = 1
        while User.objects.filter(username=username).exists():
            counter += 1
            username = f"{base}{counter}"
        return username


class AdminPatientDetailView(APIView):
    permission_classes = [IsStaff]

    def get_patient(self, pk):
        try:
            return patient_queryset().get(pk=pk)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)
        return Response(AdminPatientDetailSerializer(patient, context={"request": request}).data)

    def patch(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        serializer = AdminPatientUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_fields = {}
        for field in ("first_name", "last_name", "email"):
            if field in data:
                user_fields[field] = data[field]
        if user_fields:
            for key, value in user_fields.items():
                setattr(patient, key, value)
            patient.save(update_fields=list(user_fields.keys()))

        profile_fields = {}
        for field in ("height", "weight", "date_of_birth", "phone", "admin_notes"):
            if field in data:
                profile_fields[field] = data[field]

        if profile_fields:
            profile, _ = PatientProfile.objects.get_or_create(user=patient)
            for key, value in profile_fields.items():
                setattr(profile, key, value)
            profile.save()

        patient = self.get_patient(pk)
        return Response(
            AdminPatientDetailSerializer(patient, context={"request": request}).data
        )


class AdminPatientWeightView(APIView):
    permission_classes = [IsStaff]

    def post(self, request, pk):
        try:
            patient = User.objects.get(pk=pk, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        serializer = AdminWeightEntrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entry = WeightHistory.objects.create(
            patient=patient,
            weight=serializer.validated_data["weight"],
        )
        profile, _ = PatientProfile.objects.get_or_create(user=patient)
        profile.weight = entry.weight
        profile.save(update_fields=["weight", "updated_at"])

        patient = patient_queryset().get(pk=pk)
        return Response(
            {
                "entry": WeightHistorySerializer(entry).data,
                "patient": AdminPatientDetailSerializer(
                    patient, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AdminPatientPhotoListCreateView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_patient(self, pk):
        try:
            return User.objects.get(pk=pk, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        photos = PatientProgressPhoto.objects.filter(patient=patient).select_related(
            "uploaded_by"
        )
        return Response(
            PatientProgressPhotoSerializer(
                photos, many=True, context={"request": request}
            ).data
        )

    def post(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        serializer = PatientProgressPhotoUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        photo = serializer.save(patient=patient, uploaded_by=request.user)
        return Response(
            PatientProgressPhotoSerializer(photo, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class AdminPatientPhotoDeleteView(APIView):
    permission_classes = [IsStaff]

    def delete(self, request, pk, photo_id):
        try:
            photo = PatientProgressPhoto.objects.get(pk=photo_id, patient_id=pk)
        except PatientProgressPhoto.DoesNotExist:
            return Response({"detail": "Fotoğraf bulunamadı."}, status=404)

        if photo.image:
            photo.image.delete(save=False)
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPatientPostureListCreateView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_patient(self, pk):
        try:
            return User.objects.get(pk=pk, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        assessments = PostureAssessment.objects.filter(
            patient=patient
        ).select_related("created_by")
        return Response(
            PostureAssessmentSerializer(
                assessments, many=True, context={"request": request}
            ).data
        )

    def post(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        # Çoklu form gönderiminde `metrics` JSON metni olarak gelir.
        data = request.data.copy()
        raw_metrics = data.get("metrics")
        if isinstance(raw_metrics, str):
            import json

            try:
                data["metrics"] = json.loads(raw_metrics) if raw_metrics else {}
            except (ValueError, TypeError):
                data["metrics"] = {}

        serializer = PostureAssessmentCreateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        assessment = serializer.save(patient=patient, created_by=request.user)

        return Response(
            PostureAssessmentSerializer(
                assessment, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )


class AdminPatientPostureDeleteView(APIView):
    permission_classes = [IsStaff]

    def delete(self, request, pk, assessment_id):
        try:
            assessment = PostureAssessment.objects.get(
                pk=assessment_id, patient_id=pk
            )
        except PostureAssessment.DoesNotExist:
            return Response({"detail": "Analiz bulunamadı."}, status=404)

        if assessment.image:
            assessment.image.delete(save=False)
        assessment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPatientPackageListCreateView(APIView):
    permission_classes = [IsStaff]

    def get_patient(self, pk):
        try:
            return User.objects.get(pk=pk, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return None

    def get(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)
        packages = SessionPackage.objects.filter(patient=patient).select_related(
            "created_by"
        )
        return Response(SessionPackageSerializer(packages, many=True).data)

    def post(self, request, pk):
        patient = self.get_patient(pk)
        if not patient:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        serializer = SessionPackageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        plan = None
        plan_id = data.get("plan_id")
        if plan_id:
            try:
                plan = PackagePlan.objects.get(pk=plan_id)
            except PackagePlan.DoesNotExist:
                return Response({"detail": "Paket planı bulunamadı."}, status=404)

        # Plan seçildiyse ad/seans/fiyat plandan kopyalanır (snapshot);
        # manuel girilen değerler varsa onlar önceliklidir.
        name = data.get("name") or (plan.name if plan else "")
        total_sessions = data.get("total_sessions") or (
            plan.total_sessions if plan else 12
        )
        price = data.get("price")
        if price is None and plan is not None:
            price = plan.price

        is_paid = data.get("is_paid", False)
        package = SessionPackage.objects.create(
            patient=patient,
            created_by=request.user,
            plan=plan,
            name=name,
            total_sessions=total_sessions,
            price=price,
            is_paid=is_paid,
            paid_at=timezone.localdate() if is_paid else None,
            purchased_at=data.get("purchased_at") or timezone.localdate(),
            note=data.get("note", ""),
        )

        # Pakete bağlanmamış, yaklaşan aktif randevuları bu pakete bağla
        Appointment.objects.filter(
            patient=patient,
            package__isnull=True,
            status__in=[AppointmentStatus.PENDING, AppointmentStatus.APPROVED],
            appointment_datetime__gte=timezone.now(),
        ).update(package=package)

        return Response(
            SessionPackageSerializer(package).data,
            status=status.HTTP_201_CREATED,
        )


class AdminPatientPackageDetailView(APIView):
    permission_classes = [IsStaff]

    def get_object(self, pk, package_id):
        try:
            return SessionPackage.objects.get(pk=package_id, patient_id=pk)
        except SessionPackage.DoesNotExist:
            return None

    def patch(self, request, pk, package_id):
        package = self.get_object(pk, package_id)
        if not package:
            return Response({"detail": "Paket bulunamadı."}, status=404)

        if "is_active" in request.data:
            package.is_active = bool(request.data["is_active"])
        if "note" in request.data:
            package.note = request.data["note"]
        if "total_sessions" in request.data:
            try:
                total = int(request.data["total_sessions"])
                if total >= 1:
                    package.total_sessions = total
            except (TypeError, ValueError):
                pass
        if "price" in request.data:
            try:
                package.price = (
                    None
                    if request.data["price"] in (None, "")
                    else request.data["price"]
                )
            except (TypeError, ValueError):
                pass
        if "is_paid" in request.data:
            package.is_paid = bool(request.data["is_paid"])
            package.paid_at = timezone.localdate() if package.is_paid else None
        package.save()
        return Response(SessionPackageSerializer(package).data)

    def delete(self, request, pk, package_id):
        package = self.get_object(pk, package_id)
        if not package:
            return Response({"detail": "Paket bulunamadı."}, status=404)
        package.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPackagePlanListCreateView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        plans = PackagePlan.objects.all()
        return Response(PackagePlanSerializer(plans, many=True, context={"request": request}).data)

    def post(self, request):
        serializer = PackagePlanSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminPackagePlanDetailView(APIView):
    permission_classes = [IsStaff]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self, plan_id):
        try:
            return PackagePlan.objects.get(pk=plan_id)
        except PackagePlan.DoesNotExist:
            return None

    def patch(self, request, plan_id):
        plan = self.get_object(plan_id)
        if not plan:
            return Response({"detail": "Paket planı bulunamadı."}, status=404)
        serializer = PackagePlanSerializer(plan, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, plan_id):
        plan = self.get_object(plan_id)
        if not plan:
            return Response({"detail": "Paket planı bulunamadı."}, status=404)
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAppointmentListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        status_filter = request.query_params.get("status")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        queryset = Appointment.objects.select_related("patient", "doctor").all()

        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if date_from:
            queryset = queryset.filter(appointment_datetime__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(appointment_datetime__date__lte=date_to)

        return Response(AdminAppointmentSerializer(queryset, many=True).data)

    def post(self, request):
        from appointments.schedule_service import is_valid_appointment_slot

        serializer = AdminAppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            patient = User.objects.get(
                pk=data["patient_id"], is_staff=False, is_superuser=False
            )
        except User.DoesNotExist:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        try:
            doctor = User.objects.get(pk=data["doctor"], is_staff=True)
        except User.DoesNotExist:
            return Response({"detail": "Doktor bulunamadı."}, status=404)

        appointment_datetime = data["appointment_datetime"]
        if not is_valid_appointment_slot(appointment_datetime, doctor.id):
            return Response(
                {
                    "detail": (
                        "Seçilen saat müsait değil (dolu, tatil veya çalışma "
                        "saatleri dışında)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_package = (
            patient.session_packages.filter(is_active=True)
            .order_by("-purchased_at", "-created_at")
            .first()
        )

        appointment = Appointment(
            patient=patient,
            doctor=doctor,
            appointment_datetime=appointment_datetime,
            status=AppointmentStatus.APPROVED,
            note=data.get("note", ""),
            package=active_package,
        )
        appointment._notification_actor = request.user
        appointment.save()

        return Response(
            AdminAppointmentSerializer(appointment).data,
            status=status.HTTP_201_CREATED,
        )


class AdminBodyMeasurementListCreateView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, patient_id):
        measurements = BodyMeasurement.objects.filter(patient_id=patient_id)
        return Response(BodyMeasurementSerializer(measurements, many=True).data)

    def post(self, request, patient_id):
        serializer = BodyMeasurementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(patient_id=patient_id)

        try:
            patient = User.objects.get(pk=patient_id)
            from accounts.push_service import send_push_to_users
            send_push_to_users(
                [patient],
                title="Yeni Ölçümleriniz Eklendi",
                body="Terapistiniz vücut ölçümlerinizi güncelledi. Görüntülemek için tıklayın.",
                data={"notification_type": "measurement_added", "link": "/hesabim/olcumler"},
            )
        except Exception:
            pass

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminBodyMeasurementDetailView(APIView):
    permission_classes = [IsStaff]

    def patch(self, request, patient_id, measurement_id):
        try:
            m = BodyMeasurement.objects.get(pk=measurement_id, patient_id=patient_id)
        except BodyMeasurement.DoesNotExist:
            return Response({"detail": "Bulunamadı."}, status=404)
        serializer = BodyMeasurementSerializer(m, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, patient_id, measurement_id):
        try:
            m = BodyMeasurement.objects.get(pk=measurement_id, patient_id=patient_id)
        except BodyMeasurement.DoesNotExist:
            return Response({"detail": "Bulunamadı."}, status=404)
        m.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAppointmentStatusView(APIView):
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.select_related("patient", "doctor").get(
                pk=pk
            )
        except Appointment.DoesNotExist:
            return Response({"detail": "Randevu bulunamadı."}, status=404)

        serializer = AdminAppointmentStatusSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "status" in data:
            appointment.status = data["status"]
        if "note" in data:
            appointment.note = data["note"]
        appointment._notification_actor = request.user
        appointment.save()

        return Response(AdminAppointmentSerializer(appointment).data)


# ─── FAQ Views ───────────────────────────────────────────────────────────────

class AdminFaqListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        faqs = Faq.objects.all()
        return Response(FaqSerializer(faqs, many=True).data)

    def post(self, request):
        serializer = FaqSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminFaqDetailView(APIView):
    permission_classes = [IsStaff]

    def _get(self, faq_id):
        try:
            return Faq.objects.get(pk=faq_id)
        except Faq.DoesNotExist:
            return None

    def put(self, request, faq_id):
        faq = self._get(faq_id)
        if not faq:
            return Response({"detail": "Bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        serializer = FaqSerializer(faq, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, faq_id):
        faq = self._get(faq_id)
        if not faq:
            return Response({"detail": "Bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        faq.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicFaqListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        faqs = Faq.objects.filter(is_active=True)
        return Response(FaqSerializer(faqs, many=True).data)


# ─── Diet Views ───────────────────────────────────────────────────────────────

class AdminDietItemListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        items = DietItem.objects.filter(is_active=True)
        return Response(DietItemSerializer(items, many=True).data)

    def post(self, request):
        s = DietItemSerializer(data=request.data)
        if s.is_valid():
            s.save()
            return Response(s.data, status=status.HTTP_201_CREATED)
        return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminDietItemDetailView(APIView):
    permission_classes = [IsStaff]

    def _get(self, pk):
        try:
            return DietItem.objects.get(pk=pk)
        except DietItem.DoesNotExist:
            return None

    def put(self, request, pk):
        item = self._get(pk)
        if not item:
            return Response({"detail": "Bulunamadı."}, status=404)
        s = DietItemSerializer(item, data=request.data, partial=True)
        if s.is_valid():
            s.save()
            return Response(s.data)
        return Response(s.errors, status=400)

    def delete(self, request, pk):
        item = self._get(pk)
        if not item:
            return Response({"detail": "Bulunamadı."}, status=404)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPatientDietPlanListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, patient_id):
        plans = (
            DietPlan.objects.filter(patient_id=patient_id)
            .prefetch_related("plan_items__diet_item")
            .order_by("-date", "meal_type")
        )
        return Response(DietPlanSerializer(plans, many=True).data)

    def post(self, request, patient_id):
        try:
            patient = User.objects.get(pk=patient_id, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)

        items_data = request.data.pop("items", []) if isinstance(request.data, dict) else []
        data = {**request.data, "patient": patient.pk}
        s = DietPlanSerializer(data=data)
        if not s.is_valid():
            return Response(s.errors, status=400)

        plan = s.save(assigned_by=request.user, patient=patient)

        for item_data in items_data:
            diet_item_id = item_data.get("diet_item_id")
            quantity = item_data.get("quantity", 1)
            note = item_data.get("note", "")
            try:
                diet_item = DietItem.objects.get(pk=diet_item_id)
                DietPlanItem.objects.create(plan=plan, diet_item=diet_item, quantity=quantity, note=note)
            except DietItem.DoesNotExist:
                pass

        plan.refresh_from_db()

        try:
            from accounts.push_service import send_push_to_users
            send_push_to_users(
                [patient],
                title="Yeni Diyet Planınız Hazır",
                body="Terapistiniz size yeni bir diyet planı atadı. Kontrol edin!",
                data={"notification_type": "diet_assigned", "link": "/hesabim/diyet"},
            )
        except Exception:
            pass

        return Response(DietPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class AdminPatientDietPlanDetailView(APIView):
    permission_classes = [IsStaff]

    def _get(self, patient_id, plan_id):
        try:
            return DietPlan.objects.prefetch_related("plan_items__diet_item").get(
                pk=plan_id, patient_id=patient_id
            )
        except DietPlan.DoesNotExist:
            return None

    def put(self, request, patient_id, plan_id):
        plan = self._get(patient_id, plan_id)
        if not plan:
            return Response({"detail": "Bulunamadı."}, status=404)

        items_data = request.data.pop("items", []) if isinstance(request.data, dict) else []
        s = DietPlanSerializer(plan, data=request.data, partial=True)
        if not s.is_valid():
            return Response(s.errors, status=400)
        s.save()

        if items_data is not None:
            plan.plan_items.all().delete()
            for item_data in items_data:
                try:
                    diet_item = DietItem.objects.get(pk=item_data.get("diet_item_id"))
                    DietPlanItem.objects.create(
                        plan=plan,
                        diet_item=diet_item,
                        quantity=item_data.get("quantity", 1),
                        note=item_data.get("note", ""),
                    )
                except DietItem.DoesNotExist:
                    pass

        plan.refresh_from_db()
        return Response(DietPlanSerializer(plan).data)

    def delete(self, request, patient_id, plan_id):
        plan = self._get(patient_id, plan_id)
        if not plan:
            return Response({"detail": "Bulunamadı."}, status=404)
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PatientDietPlanListView(APIView):
    """Hasta kendi diyet planlarını görür."""

    def get(self, request):
        plans = (
            DietPlan.objects.filter(patient=request.user, is_active=True)
            .prefetch_related("plan_items__diet_item")
            .order_by("-date", "meal_type")
        )
        return Response(DietPlanSerializer(plans, many=True).data)


class AdminAttendanceView(APIView):
    """Öğrenci için belirli bir güne ait katılım kaydı oluştur veya güncelle."""
    permission_classes = [IsStaff]

    def post(self, request, patient_id):
        patient = User.objects.filter(pk=patient_id, is_staff=False).first()
        if not patient:
            return Response({"detail": "Bulunamadı."}, status=404)

        record_status = request.data.get("status")
        if record_status not in ("came", "no_show"):
            return Response({"detail": "Geçersiz durum."}, status=400)

        date = request.data.get("date") or timezone.localdate()
        package_id = request.data.get("package_id")

        session_package = None
        if package_id:
            from accounts.models import SessionPackage
            session_package = SessionPackage.objects.filter(pk=package_id, patient=patient, is_active=True).first()

        record, _ = AttendanceRecord.objects.update_or_create(
            patient=patient,
            date=date,
            defaults={
                "status": record_status,
                "marked_by": request.user,
                "session_package": session_package,
            },
        )
        return Response({"id": record.id, "status": record.status, "date": str(record.date)})

    def delete(self, request, patient_id):
        date = request.query_params.get("date") or str(timezone.localdate())
        AttendanceRecord.objects.filter(patient_id=patient_id, date=date).delete()
        return Response(status=204)


class AdminTestimonialListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        from .site_serializers import TestimonialSerializer
        from .models import Testimonial
        items = Testimonial.objects.all()
        return Response(TestimonialSerializer(items, many=True).data)

    def post(self, request):
        from .site_serializers import TestimonialSerializer
        s = TestimonialSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data, status=201)


class AdminTestimonialDetailView(APIView):
    permission_classes = [IsStaff]

    def _get(self, pk):
        from .models import Testimonial
        return Testimonial.objects.filter(pk=pk).first()

    def put(self, request, pk):
        from .site_serializers import TestimonialSerializer
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Bulunamadı."}, status=404)
        s = TestimonialSerializer(obj, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)

    def delete(self, request, pk):
        obj = self._get(pk)
        if not obj:
            return Response({"detail": "Bulunamadı."}, status=404)
        obj.delete()
        return Response(status=204)


class PublicTestimonialListView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        from .site_serializers import TestimonialSerializer
        from .models import Testimonial
        items = Testimonial.objects.filter(is_active=True)
        return Response(TestimonialSerializer(items, many=True).data)


def _landing_crud_views(Model, Serializer):
    """Returns (ListCreateView, DetailView, PublicView) classes for a landing content model."""
    class AdminListView(APIView):
        permission_classes = [IsStaff]
        def get(self, request):
            return Response(Serializer(Model.objects.all(), many=True).data)
        def post(self, request):
            s = Serializer(data=request.data)
            s.is_valid(raise_exception=True)
            s.save()
            return Response(s.data, status=201)

    class AdminDetailView(APIView):
        permission_classes = [IsStaff]
        def put(self, request, pk):
            obj = Model.objects.filter(pk=pk).first()
            if not obj:
                return Response({"detail": "Bulunamadı."}, status=404)
            s = Serializer(obj, data=request.data, partial=True)
            s.is_valid(raise_exception=True)
            s.save()
            return Response(s.data)
        def delete(self, request, pk):
            obj = Model.objects.filter(pk=pk).first()
            if not obj:
                return Response({"detail": "Bulunamadı."}, status=404)
            obj.delete()
            return Response(status=204)

    class PublicView(APIView):
        permission_classes = []
        authentication_classes = []
        def get(self, request):
            return Response(Serializer(Model.objects.filter(is_active=True), many=True).data)

    return AdminListView, AdminDetailView, PublicView


from .site_serializers import LandingServiceSerializer, LandingTreatmentSerializer, LandingWhyUsItemSerializer
from .models import LandingService, LandingTreatment, LandingWhyUsItem

AdminLandingServiceListView, AdminLandingServiceDetailView, PublicLandingServiceView = \
    _landing_crud_views(LandingService, LandingServiceSerializer)

AdminLandingTreatmentListView, AdminLandingTreatmentDetailView, PublicLandingTreatmentView = \
    _landing_crud_views(LandingTreatment, LandingTreatmentSerializer)

AdminLandingWhyUsListView, AdminLandingWhyUsDetailView, PublicLandingWhyUsView = \
    _landing_crud_views(LandingWhyUsItem, LandingWhyUsItemSerializer)


class AdminSendNotificationView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        from .push_service import send_push_to_users

        title = request.data.get("title", "").strip()
        body = request.data.get("body", "").strip()
        patient_ids = request.data.get("patient_ids")

        if not title or not body:
            return Response(
                {"detail": "Başlık ve mesaj alanları zorunludur."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if patient_ids:
            users = list(
                User.objects.filter(
                    pk__in=patient_ids, is_staff=False, is_superuser=False, is_active=True
                )
            )
        else:
            users = list(
                User.objects.filter(is_staff=False, is_superuser=False, is_active=True)
            )

        if users:
            send_push_to_users(
                users,
                title=title,
                body=body,
                data={"notification_type": "general", "link": "/hesabim"},
            )

        return Response({"sent_to": len(users)}, status=status.HTTP_200_OK)


class AdminOnboardingQuestionListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        questions = OnboardingQuestion.objects.all()
        return Response(OnboardingQuestionSerializer(questions, many=True).data)

    def post(self, request):
        serializer = OnboardingQuestionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminOnboardingQuestionDetailView(APIView):
    permission_classes = [IsStaff]

    def _get(self, pk):
        try:
            return OnboardingQuestion.objects.get(pk=pk)
        except OnboardingQuestion.DoesNotExist:
            return None

    def put(self, request, pk):
        question = self._get(pk)
        if not question:
            return Response({"detail": "Bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        serializer = OnboardingQuestionSerializer(question, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        question = self._get(pk)
        if not question:
            return Response({"detail": "Bulunamadı."}, status=status.HTTP_404_NOT_FOUND)
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminPatientOnboardingAnswersView(APIView):
    permission_classes = [IsStaff]

    def get(self, request, pk):
        try:
            patient = User.objects.get(pk=pk, is_staff=False, is_superuser=False)
        except User.DoesNotExist:
            return Response({"detail": "Öğrenci bulunamadı."}, status=404)
        answers = OnboardingAnswer.objects.filter(user=patient).select_related("question")
        return Response(OnboardingAnswerSerializer(answers, many=True).data)
