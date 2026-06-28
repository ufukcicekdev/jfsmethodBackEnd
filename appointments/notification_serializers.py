from rest_framework import serializers

from .models import AdminNotification


class AdminNotificationSerializer(serializers.ModelSerializer):
    link = serializers.SerializerMethodField()
    type_label = serializers.CharField(source="get_notification_type_display", read_only=True)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AdminNotification
        fields = [
            "id",
            "notification_type",
            "type_label",
            "title",
            "message",
            "link",
            "actor_name",
            "is_read",
            "created_at",
        ]

    def get_link(self, obj):
        if obj.appointment_id:
            return "/panel/randevular"
        if obj.notification_type == "patient_registered" and obj.actor_id:
            return f"/panel/ogrenciler/{obj.actor_id}"
        return "/panel"

    def get_actor_name(self, obj):
        if not obj.actor:
            return None
        return obj.actor.get_full_name() or obj.actor.username
