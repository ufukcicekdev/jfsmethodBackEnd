from rest_framework import serializers

from .models import PatientNotification


class PatientNotificationSerializer(serializers.ModelSerializer):
    type_label = serializers.SerializerMethodField()

    class Meta:
        model = PatientNotification
        fields = [
            "id",
            "notification_type",
            "type_label",
            "title",
            "message",
            "link",
            "is_read",
            "created_at",
        ]

    def get_type_label(self, obj):
        labels = {
            "appointment": "Randevu",
            "exercise": "Egzersiz",
            "general": "Genel",
        }
        return labels.get(obj.notification_type, "Bildirim")
