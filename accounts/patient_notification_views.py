from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PatientNotification
from .patient_notification_serializers import PatientNotificationSerializer


class PatientNotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.is_staff:
            return Response(
                {"detail": "Personel bildirimleri admin panelinden görüntülenir."},
                status=status.HTTP_403_FORBIDDEN,
            )
        queryset = PatientNotification.objects.filter(user=request.user)[:50]
        unread_count = PatientNotification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return Response(
            {
                "unread_count": unread_count,
                "notifications": PatientNotificationSerializer(
                    queryset, many=True
                ).data,
            }
        )


class PatientNotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        try:
            notification = PatientNotification.objects.get(
                pk=pk, user=request.user
            )
        except PatientNotification.DoesNotExist:
            return Response({"detail": "Bildirim bulunamadı."}, status=404)

        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(PatientNotificationSerializer(notification).data)


class PatientNotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = PatientNotification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return Response({"marked_read": updated})
