import logging
import threading

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .admin_serializers import PackagePlanSerializer
from .models import FCMDevice, PackagePlan, PatientProfile, WeightHistory
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    ForgotPasswordSerializer,
    PatientProfileSerializer,
    ResetPasswordConfirmSerializer,
    UserPublicSerializer,
    UserRegistrationSerializer,
    WeightHistorySerializer,
)

logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        from appointments.notification_service import notify_patient_registered

        notify_patient_registered(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": UserPublicSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserPublicSerializer(request.user).data)


class PatientProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = PatientProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if self.request.user.is_staff:
            from rest_framework.exceptions import NotFound

            raise NotFound("Staff users do not have a patient profile.")
        profile, _ = PatientProfile.objects.get_or_create(user=self.request.user)
        return profile


class MyPackagesView(APIView):
    """Hastanın kendi seans paketlerini ve kalan/kullanılan bilgisini döner."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from .admin_serializers import SessionPackageSerializer
        from .models import SessionPackage

        packages = SessionPackage.objects.filter(
            patient=request.user
        ).select_related("created_by")
        return Response(SessionPackageSerializer(packages, many=True).data)


class FCMDeviceRegisterView(APIView):
    """PWA istemcisinden gelen FCM token'ını kullanıcıya kaydeder."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response(
                {"detail": "token alanı zorunludur."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]

        FCMDevice.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "user_agent": user_agent,
                "is_active": True,
            },
        )
        return Response({"detail": "Cihaz kaydedildi."}, status=status.HTTP_200_OK)


class FCMDeviceUnregisterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if token:
            FCMDevice.objects.filter(token=token, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Şifreniz güncellendi."})


def _send_password_reset_email(user_id: int, frontend_origin: str):
    try:
        user = User.objects.get(pk=user_id)
        if not user.email:
            return
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{frontend_origin.rstrip('/')}/sifre-sifirla?uid={uid}&token={token}"
        send_mail(
            subject="FizyoTech — Şifre Sıfırlama",
            message=(
                f"Sayın {user.get_full_name() or user.username},\n\n"
                f"Şifrenizi sıfırlamak için aşağıdaki bağlantıyı kullanın:\n"
                f"{reset_url}\n\n"
                f"Bu bağlantı güvenlik nedeniyle sınırlı süre geçerlidir.\n\n"
                f"FizyoTech Ekibi"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Password reset email failed for user %s", user_id)


class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            origin = request.headers.get("Origin") or "http://localhost:3000"
            thread = threading.Thread(
                target=_send_password_reset_email,
                args=(user.pk, origin),
                daemon=True,
            )
            thread.start()

        return Response(
            {
                "detail": (
                    "E-posta adresiniz kayıtlıysa şifre sıfırlama bağlantısı gönderildi."
                )
            }
        )


class ResetPasswordConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid, is_active=True)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Geçersiz veya süresi dolmuş bağlantı."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, data["token"]):
            return Response(
                {"detail": "Geçersiz veya süresi dolmuş bağlantı."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Şifreniz başarıyla güncellendi. Giriş yapabilirsiniz."})


class PublicPackagePlansView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = PackagePlan.objects.filter(is_active=True)
        return Response(PackagePlanSerializer(plans, many=True, context={"request": request}).data)


class WeightHistoryListCreateView(generics.ListCreateAPIView):
    serializer_class = WeightHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WeightHistory.objects.filter(patient=self.request.user)

    def perform_create(self, serializer):
        entry = serializer.save()
        profile, _ = PatientProfile.objects.get_or_create(user=self.request.user)
        profile.weight = entry.weight
        profile.save(update_fields=["weight", "updated_at"])
