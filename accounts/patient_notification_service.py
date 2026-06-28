from .models import PatientNotification


def create_patient_notification(
    user,
    *,
    notification_type: str = "general",
    title: str,
    message: str,
    link: str = "/hesabim",
):
    return PatientNotification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )


def create_patient_notifications_for_users(
    user_ids,
    *,
    notification_type: str = "general",
    title: str,
    message: str,
    link: str = "/hesabim",
):
    from django.contrib.auth.models import User

    patients = User.objects.filter(id__in=user_ids, is_staff=False)
    PatientNotification.objects.bulk_create(
        [
            PatientNotification(
                user=patient,
                notification_type=notification_type,
                title=title,
                message=message,
                link=link,
            )
            for patient in patients
        ]
    )
