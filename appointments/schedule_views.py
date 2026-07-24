from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaff

from django.utils import timezone

from .models import ClinicHoliday, ClinicScheduleSettings, SlotBlock, WorkingDay
from .day_cancellation_service import cancel_day, get_day_cancellation_preview
from .schedule_serializers import (
    ClinicHolidaySerializer,
    ClinicScheduleUpdateSerializer,
    DayCancellationPreviewSerializer,
    DayCancellationSerializer,
    SlotBlockSerializer,
    WorkingDaySerializer,
)
from .schedule_service import ensure_default_schedule


class AdminScheduleView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        ensure_default_schedule()
        settings = ClinicScheduleSettings.get_solo()
        working_days = WorkingDay.objects.all()
        holidays = ClinicHoliday.objects.filter(date__gte=timezone.localdate())

        return Response(
            {
                "slot_duration_minutes": settings.slot_duration_minutes,
                "slot_capacity": settings.slot_capacity,
                "slot_break_minutes": settings.slot_break_minutes,
                "free_cancel_hours": settings.free_cancel_hours,
                "late_cancel_penalty_minutes": settings.late_cancel_penalty_minutes,
                "reminder_24h_enabled": settings.reminder_24h_enabled,
                "reminder_1h_enabled": settings.reminder_1h_enabled,
                "reminder_custom_minutes": settings.reminder_custom_minutes,
                "working_days": WorkingDaySerializer(working_days, many=True).data,
                "holidays": ClinicHolidaySerializer(holidays, many=True).data,
            }
        )

    def put(self, request):
        ensure_default_schedule()
        serializer = ClinicScheduleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        settings = ClinicScheduleSettings.get_solo()
        settings.slot_duration_minutes = data["slot_duration_minutes"]
        update_fields = ["slot_duration_minutes"]
        for field in (
            "slot_capacity", "slot_break_minutes", "free_cancel_hours",
            "late_cancel_penalty_minutes", "reminder_24h_enabled",
            "reminder_1h_enabled", "reminder_custom_minutes",
        ):
            if field in data:
                setattr(settings, field, data[field])
                update_fields.append(field)
        settings.save(update_fields=update_fields)

        for day_data in data["working_days"]:
            WorkingDay.objects.filter(day_of_week=day_data["day_of_week"]).update(
                is_working=day_data["is_working"],
                start_time=day_data["start_time"],
                end_time=day_data["end_time"],
            )

        working_days = WorkingDay.objects.all()
        holidays = ClinicHoliday.objects.filter(date__gte=timezone.localdate())
        return Response(
            {
                "slot_duration_minutes": settings.slot_duration_minutes,
                "slot_capacity": settings.slot_capacity,
                "slot_break_minutes": settings.slot_break_minutes,
                "free_cancel_hours": settings.free_cancel_hours,
                "late_cancel_penalty_minutes": settings.late_cancel_penalty_minutes,
                "reminder_24h_enabled": settings.reminder_24h_enabled,
                "reminder_1h_enabled": settings.reminder_1h_enabled,
                "reminder_custom_minutes": settings.reminder_custom_minutes,
                "working_days": WorkingDaySerializer(working_days, many=True).data,
                "holidays": ClinicHolidaySerializer(holidays, many=True).data,
            }
        )


class AdminHolidayListCreateView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        serializer = ClinicHolidaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        holiday = serializer.save()
        return Response(
            ClinicHolidaySerializer(holiday).data,
            status=status.HTTP_201_CREATED,
        )


class AdminHolidayDeleteView(APIView):
    permission_classes = [IsStaff]

    def delete(self, request, pk):
        try:
            holiday = ClinicHoliday.objects.get(pk=pk)
        except ClinicHoliday.DoesNotExist:
            return Response({"detail": "Tatil günü bulunamadı."}, status=404)
        holiday.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminCancelDayPreviewView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        serializer = DayCancellationPreviewSerializer(
            data={"date": request.query_params.get("date")}
        )
        serializer.is_valid(raise_exception=True)
        target_date = serializer.validated_data["date"]

        if target_date < timezone.localdate():
            return Response(
                {"detail": "Geçmiş bir tarih için önizleme yapılamaz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(get_day_cancellation_preview(target_date))


class AdminCancelDayView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        serializer = DayCancellationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target_date = data["date"]

        if target_date < timezone.localdate():
            return Response(
                {"detail": "Geçmiş bir tarih iptal edilemez."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = cancel_day(
            target_date=target_date,
            reason=data["reason"],
            admin_user=request.user,
            add_holiday=data.get("add_holiday", True),
        )

        if result["cancelled_count"] == 0:
            return Response(
                {
                    "detail": "Bu tarihte iptal edilecek aktif randevu bulunmuyor.",
                    **result,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": (
                    f"{result['cancelled_count']} randevu iptal edildi. "
                    f"{result['emails_scheduled']} öğrenciye bilgilendirme e-postası gönderiliyor."
                ),
                **result,
            },
            status=status.HTTP_200_OK,
        )


class AdminSlotBlockListCreateView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        from django.utils import timezone as tz
        blocks = SlotBlock.objects.filter(date__gte=tz.localdate())
        return Response(SlotBlockSerializer(blocks, many=True).data)

    def post(self, request):
        serializer = SlotBlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        block = serializer.save()
        return Response(SlotBlockSerializer(block).data, status=status.HTTP_201_CREATED)


class AdminSlotBlockDeleteView(APIView):
    permission_classes = [IsStaff]

    def delete(self, request, pk):
        try:
            block = SlotBlock.objects.get(pk=pk)
        except SlotBlock.DoesNotExist:
            return Response({"detail": "Bulunamadı."}, status=404)
        block.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublicCancelPolicyView(APIView):
    """Randevu iptal politikasını herkese açık döndürür (sözleşme metni için)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from .models import ClinicScheduleSettings
        settings = ClinicScheduleSettings.objects.filter(pk=1).first()
        if not settings:
            return Response({
                "free_cancel_hours": 6,
                "late_cancel_penalty_minutes": 30,
            })
        return Response({
            "free_cancel_hours": settings.free_cancel_hours,
            "late_cancel_penalty_minutes": settings.late_cancel_penalty_minutes,
        })
