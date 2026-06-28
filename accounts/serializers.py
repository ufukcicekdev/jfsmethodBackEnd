from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from kvkk.services import log_registration_consents

from .models import PatientProfile, WeightHistory


class UserPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    onboarding_completed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_staff",
            "is_superuser",
            "onboarding_completed",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_onboarding_completed(self, obj):
        if obj.is_staff or obj.is_superuser:
            return True
        try:
            return obj.patient_profile.onboarding_completed
        except Exception:
            return False


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["is_staff"] = user.is_staff
        token["is_superuser"] = user.is_superuser
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserPublicSerializer(self.user).data
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    kvkk_accepted = serializers.BooleanField(write_only=True)
    acik_riza_accepted = serializers.BooleanField(write_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "first_name",
            "last_name",
            "kvkk_accepted",
            "acik_riza_accepted",
        ]
        extra_kwargs = {"email": {"required": True}}

    def validate(self, attrs):
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
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        kvkk_accepted = validated_data.pop("kvkk_accepted")
        acik_riza_accepted = validated_data.pop("acik_riza_accepted")
        request = self.context["request"]

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
        )
        PatientProfile.objects.create(user=user)

        log_registration_consents(
            request,
            user,
            kvkk_accepted=kvkk_accepted,
            acik_riza_accepted=acik_riza_accepted,
        )

        return user


class PatientProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = PatientProfile
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "height",
            "weight",
            "date_of_birth",
            "phone",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mevcut şifre hatalı.")
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class WeightHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightHistory
        fields = ["id", "weight", "recorded_at"]
        read_only_fields = ["id", "recorded_at"]

    def create(self, validated_data):
        validated_data["patient"] = self.context["request"].user
        return super().create(validated_data)
