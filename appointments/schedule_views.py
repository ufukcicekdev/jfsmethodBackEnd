from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaff

from django.utils import timezone

from .models import ClinicHoliday, ClinicScheduleSettings, WorkingDay
from .day_cancellation_service import cancel_day, get_day_cancellation_preview
from .schedule_serializers import (
    ClinicHolidaySerializer,
    ClinicScheduleUpdateSerializer,
    DayCancellationPreviewSerializer,
    DayCancellationSerializer,
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
        if "slot_capacity" in data:
            settings.slot_capacity = data["slot_capacity"]
            update_fields.append("slot_capacity")
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
