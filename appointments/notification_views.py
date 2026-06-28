from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsStaff

from .models import AdminNotification
from .notification_serializers import AdminNotificationSerializer


class AdminNotificationListView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        queryset = AdminNotification.objects.select_related(
            "appointment", "actor"
        ).all()[:50]
        unread_count = AdminNotification.objects.filter(is_read=False).count()
        return Response(
            {
                "unread_count": unread_count,
                "notifications": AdminNotificationSerializer(
                    queryset, many=True
                ).data,
            }
        )


class AdminNotificationMarkReadView(APIView):
    permission_classes = [IsStaff]

    def patch(self, request, pk):
        try:
            notification = AdminNotification.objects.get(pk=pk)
        except AdminNotification.DoesNotExist:
            return Response({"detail": "Bildirim bulunamadı."}, status=404)

        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(AdminNotificationSerializer(notification).data)


class AdminNotificationMarkAllReadView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):
        updated = AdminNotification.objects.filter(is_read=False).update(is_read=True)
        return Response({"marked_read": updated})
