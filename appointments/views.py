from datetime import datetime

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

        appointment._notification_actor = request.user
        appointment.status = AppointmentStatus.CANCELLED
        appointment.save(update_fields=["status", "updated_at"])

        return Response(AppointmentSerializer(appointment).data)


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
