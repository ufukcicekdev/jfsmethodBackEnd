from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


from .models import Appointment, AppointmentStatus
from .schedule_service import get_available_slots, is_valid_appointment_slot
from .serializers import (
    AppointmentPostponeSerializer,
    AppointmentSerializer,
    AvailableSlotSerializer,
    DoctorSerializer,
)


class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class AppointmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Appointment.objects.select_related("patient", "doctor").all()
        return Appointment.objects.filter(patient=user).select_related("doctor")

    def perform_create(self, serializer):
        appointment = serializer.save()
        from accounts.audit import log_action
        log_action("appointment_create", actor=self.request.user, request=self.request,
                   detail={"appointment_id": appointment.id,
                           "datetime": str(appointment.appointment_datetime)})


class AppointmentDetailView(generics.RetrieveAPIView):
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Appointment.objects.select_related("patient", "doctor").all()
        return Appointment.objects.filter(patient=user).select_related("doctor")


class AppointmentPostponeView(APIView):
    permission_classes = [IsDoctor]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.select_related("patient", "doctor").get(
                pk=pk
            )
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Appointment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AppointmentPostponeSerializer(
            data=request.data,
            context={"appointment": appointment},
        )
        serializer.is_valid(raise_exception=True)

        appointment.status = AppointmentStatus.POSTPONED
        appointment.appointment_datetime = serializer.validated_data[
            "appointment_datetime"
        ]
        appointment.note = serializer.validated_data["note"]
        # Saat değiştiği için hatırlatmalar yeni saate göre tekrar gönderilmeli
        appointment.reminder_24h_sent = False
        appointment.reminder_1h_sent = False
        appointment._notification_actor = request.user
        appointment.save()

        return Response(
            AppointmentSerializer(appointment).data,
            status=status.HTTP_200_OK,
        )


class AppointmentCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.select_related("patient", "doctor").get(
                pk=pk,
                patient=request.user,
            )
        except Appointment.DoesNotExist:
            return Response(
                {"detail": "Randevu bulunamadı."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if appointment.status not in [
            AppointmentStatus.PENDING,
            AppointmentStatus.APPROVED,
        ]:
            return Response(
                {"detail": "Bu randevu iptal edilemez."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .models import ClinicScheduleSettings
        settings = ClinicScheduleSettings.get_solo()
        now = timezone.now()
        time_left = appointment.appointment_datetime - now
        late_cancel = time_left <= timedelta(minutes=settings.late_cancel_penalty_minutes)

        appointment._notification_actor = request.user
        appointment.status = AppointmentStatus.CANCELLED
        appointment.save(update_fields=["status", "updated_at"])

        # Son 30 dakikada iptal → seans hakkı yakar (no_show kaydı)
        if late_cancel and appointment.package:
            from accounts.models import AttendanceRecord
            AttendanceRecord.objects.get_or_create(
                patient=appointment.patient,
                date=appointment.appointment_datetime.date(),
                defaults={
                    "session_package": appointment.package,
                    "status": "no_show",
                    "marked_by": None,
                    "note": "Son 30 dakikada iptal — seans hakkı düşüldü.",
                },
            )

        from accounts.audit import log_action
        log_action("appointment_cancel", actor=request.user, target_user=appointment.patient, request=request,
                   detail={"appointment_id": appointment.id,
                           "datetime": str(appointment.appointment_datetime),
                           "late_cancel": late_cancel})
        data = AppointmentSerializer(appointment).data
        data["late_cancel"] = late_cancel
        return Response(data)


class AvailableSlotsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .schedule_service import ensure_default_schedule

        ensure_default_schedule()
        date_str = request.query_params.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"detail": "Invalid date format. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.localdate()

        slots = get_available_slots(target_date)
        serializer = AvailableSlotSerializer(slots, many=True)
        return Response(serializer.data)


class DoctorListView(generics.ListAPIView):
    serializer_class = DoctorSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(is_staff=True, is_active=True)
