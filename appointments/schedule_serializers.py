from rest_framework import serializers

from .models import ClinicHoliday, ClinicScheduleSettings, WorkingDay


class WorkingDaySerializer(serializers.ModelSerializer):
    day_label = serializers.CharField(read_only=True)

    class Meta:
        model = WorkingDay
        fields = [
            "day_of_week",
            "day_label",
            "is_working",
            "start_time",
            "end_time",
        ]


class ClinicHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicHoliday
        fields = ["id", "date", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class DayCancellationPreviewSerializer(serializers.Serializer):
    date = serializers.DateField()


class DayCancellationSerializer(serializers.Serializer):
    date = serializers.DateField()
    reason = serializers.CharField(min_length=5, max_length=2000)
    add_holiday = serializers.BooleanField(default=True)


class ClinicScheduleSerializer(serializers.Serializer):
    slot_duration_minutes = serializers.IntegerField(min_value=15, max_value=120)
    working_days = WorkingDaySerializer(many=True)


class WorkingDayUpdateSerializer(serializers.Serializer):
    day_of_week = serializers.IntegerField(min_value=0, max_value=6)
    is_working = serializers.BooleanField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    def validate(self, attrs):
        if attrs["is_working"] and attrs["start_time"] >= attrs["end_time"]:
            raise serializers.ValidationError(
                "Bitiş saati başlangıç saatinden sonra olmalıdır."
            )
        return attrs


class ClinicScheduleUpdateSerializer(serializers.Serializer):
    slot_duration_minutes = serializers.IntegerField(min_value=15, max_value=120)
    slot_capacity = serializers.IntegerField(min_value=1, max_value=100, required=False)
    working_days = WorkingDayUpdateSerializer(many=True)

    def validate_working_days(self, value):
        if len(value) != 7:
            raise serializers.ValidationError("7 günlük program gönderilmelidir.")
        weekdays = {item["day_of_week"] for item in value}
        if weekdays != set(range(7)):
            raise serializers.ValidationError("Tüm haftanın günleri eksiksiz olmalıdır.")
        return value
