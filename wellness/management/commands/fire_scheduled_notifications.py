"""
Zamanlanmış bildirim gönderimi.
Railway Cron Service tarafından her 10 dakikada bir çalıştırılır:
  python manage.py fire_scheduled_notifications
"""

import logging
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_target_users(notification_type):
    from django.contrib.auth.models import User
    from accounts.models import FCMDevice
    from wellness.models import DailyWaterLog, DailyStepLog, ExerciseAssignment, ExerciseCompletion

    today = timezone.localdate()

    active_patient_ids = set(
        FCMDevice.objects.filter(is_active=True)
        .values_list("user__id", flat=True)
    )
    patients = User.objects.filter(
        id__in=active_patient_ids, is_staff=False, is_superuser=False, is_active=True
    )

    if notification_type == "water":
        # < 500ml içmiş olanlar (kayıt yoksa da dahil)
        logged_enough = set(
            DailyWaterLog.objects.filter(date=today, ml_consumed__gte=500)
            .values_list("patient_id", flat=True)
        )
        return [p for p in patients if p.id not in logged_enough]

    elif notification_type == "steps":
        # Bugün adım kaydı olmayanlar
        logged = set(
            DailyStepLog.objects.filter(date=today)
            .values_list("patient_id", flat=True)
        )
        return [p for p in patients if p.id not in logged]

    elif notification_type == "exercise":
        # Aktif ataması olan ama bugün tamamlamayan hastalar
        has_active = set(
            ExerciseAssignment.objects.filter(is_active=True)
            .values_list("patient_id", flat=True)
        )
        completed_today = set(
            ExerciseCompletion.objects.filter(completed_at__date=today)
            .values_list("patient_id", flat=True)
        )
        target_ids = has_active - completed_today
        return [p for p in patients if p.id in target_ids]

    else:  # custom — herkese
        return list(patients)


LINK_MAP = {
    "water": "/hesabim",
    "steps": "/hesabim",
    "exercise": "/hesabim/egzersizlerim",
    "custom": "/hesabim",
}


class Command(BaseCommand):
    help = "Zamanlanmış motivasyon bildirimlerini gönderir."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Bildirimleri göndermeden kimi hedeflediğini göster.",
        )
        parser.add_argument(
            "--force-id",
            type=int,
            help="Belirli bir schedule ID'sini zaman kontrolü olmadan çalıştır.",
        )

    def handle(self, *args, **options):
        from wellness.models import NotificationSchedule
        from accounts.push_service import send_push_to_users

        dry_run = options["dry_run"]
        force_id = options.get("force_id")

        now = timezone.localtime()
        today = timezone.localdate()
        window = timedelta(minutes=10)

        qs = NotificationSchedule.objects.filter(is_enabled=True)
        if force_id:
            qs = NotificationSchedule.objects.filter(pk=force_id)

        fired = 0
        for schedule in qs:
            if not force_id:
                # Gün kontrolü
                if today.weekday() not in (schedule.days_of_week or []):
                    continue
                # Zaman penceresi kontrolü (±10 dk)
                scheduled_dt = datetime.combine(today, schedule.send_time)
                scheduled_dt = timezone.make_aware(scheduled_dt)
                if abs((now - scheduled_dt).total_seconds()) > window.total_seconds():
                    continue
                # Bugün zaten gönderildi mi?
                if schedule.last_triggered_date == today:
                    continue

            users = _get_target_users(schedule.notification_type)
            link = LINK_MAP.get(schedule.notification_type, "/hesabim")

            if dry_run:
                self.stdout.write(
                    f"[DRY-RUN] Schedule #{schedule.id} ({schedule.get_notification_type_display()}) "
                    f"→ {len(users)} kullanıcı hedeflendi."
                )
            else:
                if users:
                    send_push_to_users(
                        users,
                        title=schedule.title,
                        body=schedule.message,
                        data={"link": link, "notification_type": schedule.notification_type},
                    )
                    logger.info(
                        "Schedule #%s gönderildi → %d kullanıcı", schedule.id, len(users)
                    )

                if not force_id:
                    schedule.last_triggered_date = today
                    schedule.save(update_fields=["last_triggered_date", "updated_at"])

                fired += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Schedule #{schedule.id} ({schedule.get_notification_type_display()}) "
                        f"gönderildi → {len(users)} kullanıcı"
                    )
                )

        if fired == 0 and not dry_run:
            self.stdout.write("Bu çalışmada gönderilecek schedule bulunamadı.")
