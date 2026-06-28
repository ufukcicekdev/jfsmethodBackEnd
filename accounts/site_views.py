from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContactMessage, SiteSettings
from .permissions import IsStaff
from .site_serializers import (
    AdminContactMessageSerializer,
    AdminSiteSettingsSerializer,
    ContactMessageCreateSerializer,
    PublicSiteSettingsSerializer,
)


class PublicSiteSettingsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        settings_obj = SiteSettings.get_solo()
        return Response(PublicSiteSettingsSerializer(settings_obj).data)


class ContactMessageCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ContactMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()

        try:
            from .push_service import send_push_to_staff

            send_push_to_staff(
                title="Yeni iletişim mesajı",
                body=f"{message.name}: {message.subject or message.message[:60]}",
                data={"link": "/panel/mesajlar", "message_id": message.pk},
            )
        except Exception:
            pass

        return Response(
            {"detail": "Mesajınız alındı. En kısa sürede dönüş yapılacaktır."},
            status=status.HTTP_201_CREATED,
        )


class AdminSiteSettingsView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        settings_obj = SiteSettings.get_solo()
        return Response(AdminSiteSettingsSerializer(settings_obj).data)

    def put(self, request):
        settings_obj = SiteSettings.get_solo()
        serializer = AdminSiteSettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AdminContactMessageListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        messages = ContactMessage.objects.all()
        unread_count = messages.filter(is_read=False).count()
        return Response(
            {
                "unread_count": unread_count,
                "messages": AdminContactMessageSerializer(messages, many=True).data,
            }
        )


class AdminContactMessageDetailView(APIView):
    permission_classes = [IsStaff]

    def get_object(self, pk):
        try:
            return ContactMessage.objects.get(pk=pk)
        except ContactMessage.DoesNotExist:
            return None

    def patch(self, request, pk):
        message = self.get_object(pk)
        if not message:
            return Response({"detail": "Mesaj bulunamadı."}, status=404)
        message.is_read = bool(request.data.get("is_read", True))
        message.save(update_fields=["is_read"])
        return Response(AdminContactMessageSerializer(message).data)

    def delete(self, request, pk):
        message = self.get_object(pk)
        if not message:
            return Response({"detail": "Mesaj bulunamadı."}, status=404)
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
