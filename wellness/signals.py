from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="wellness.UserPackageAssignment")
def create_package_notifications(sender, instance, created, **kwargs):
    """Paket atanınca öğün + egzersiz bildirimleri otomatik oluştur."""
    if not created or not instance.is_active:
        return

    from .models import UserNotificationSchedule

    # Öğün bildirimleri — sabah, öğle, akşam
    UserNotificationSchedule.objects.get_or_create(
        user=instance.user,
        package_assignment=instance,
        notification_type="meal",
        defaults={
            "title": "Öğün Takibi",
            "message": "Öğününüzü unutmayın! Fotoğraf yükleyerek takibinizi sürdürün. 🥗",
            "send_times": ["08:00", "13:00", "19:00"],
            "days_of_week": [],  # her gün
            "is_enabled": True,
        },
    )

    # Egzersiz bildirimi — akşam
    has_exercise = (
        instance.package.exercise_program_id is not None
        if hasattr(instance, "package") and instance.package
        else False
    )
    if has_exercise:
        UserNotificationSchedule.objects.get_or_create(
            user=instance.user,
            package_assignment=instance,
            notification_type="exercise",
            defaults={
                "title": "Egzersiz Zamanı",
                "message": "Bugünkü egzersiz programınızı tamamlamayı unutmayın! 💪",
                "send_times": ["18:00"],
                "days_of_week": [],
                "is_enabled": True,
            },
        )
