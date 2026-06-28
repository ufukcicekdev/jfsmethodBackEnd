from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from kvkk.services import log_appointment_consents

from .models import Appointment, AppointmentStatus
from .schedule_service import is_valid_appointment_slot


class DoctorSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "full_name"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    kvkk_accepted = serializers.BooleanField(write_only=True, required=False)
    acik_riza_accepted = serializers.BooleanField(write_only=True, required=False)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_name",
            "doctor",
            "doctor_name",
            "appointment_datetime",
            "duration_minutes",
            "status",
            "note",
            "cancellation_reason",
            "created_at",
            "updated_at",
            "kvkk_accepted",
            "acik_riza_accepted",
        ]
        read_only_fields = ["id", "patient", "status", "created_at", "updated_at"]

    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username

    def get_duration_minutes(self, obj):
        from .models import ClinicScheduleSettings

        return ClinicScheduleSettings.get_solo().slot_duration_minutes

    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username

    def validate_doctor(self, value):
        if not value.is_staff:
            raise serializers.ValidationError("Selected user is not a doctor.")
        return value

    def validate(self, attrs):
        if self.instance is None:
            if not attrs.get("kvkk_accepted"):
                raise serializers.ValidationError(
                    {
                        "kvkk_accepted": "KVKK Aydınlatma Metni onayı zorunludur.",
                    }
                )
            if not attrs.get("acik_riza_accepted"):
                raise serializers.ValidationError(
                    {
                        "acik_riza_accepted": (
                            "Özel nitelikli sağlık verileri için açık rıza onayı zorunludur."
                        ),
                    }
                )

            appointment_datetime = attrs.get("appointment_datetime")
            doctor = attrs.get("doctor")
            if appointment_datetime and doctor:
                if not is_valid_appointment_slot(appointment_datetime, doctor.id):
                    raise serializers.ValidationError(
                        {
                            "appointment_datetime": (
                                "Seçilen saat müsait değil, tatil günü veya "
                                "çalışma saatleri dışında."
                            ),
                        }
                    )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        kvkk_accepted = validated_data.pop("kvkk_accepted", False)
        acik_riza_accepted = validated_data.pop("acik_riza_accepted", False)
        request = self.context["request"]

        validated_data["patient"] = request.user

        active_package = (
            request.user.session_packages.filter(is_active=True)
            .order_by("-purchased_at", "-created_at")
            .first()
        )
        if active_package is not None:
            validated_data["package"] = active_package

        appointment = super().create(validated_data)

        log_appointment_consents(
            request,
            request.user,
            kvkk_accepted=kvkk_accepted,
            acik_riza_accepted=acik_riza_accepted,
        )

        return appointment


class AppointmentPostponeSerializer(serializers.Serializer):
    appointment_datetime = serializers.DateTimeField()
    note = serializers.CharField(required=True, allow_blank=False)

    def validate_appointment_datetime(self, value):
        from django.utils import timezone

        if value <= timezone.now():
            raise serializers.ValidationError(
                "Yeni randevu saati gelecekte olmalıdır."
            )
        return value

    def validate(self, attrs):
        appointment = self.context.get("appointment")
        if appointment and not is_valid_appointment_slot(
            attrs["appointment_datetime"],
            appointment.doctor_id,
            exclude_appointment_id=appointment.id,
        ):
            raise serializers.ValidationError(
                {
                    "appointment_datetime": (
                        "Seçilen saat müsait değil, tatil günü veya "
                        "çalışma saatleri dışında."
                    ),
                }
            )
        return attrs


class AvailableSlotSerializer(serializers.Serializer):
    datetime = serializers.DateTimeField()
    doctor_id = serializers.IntegerField()
    doctor_name = serializers.CharField()
    remaining = serializers.IntegerField(required=False)
