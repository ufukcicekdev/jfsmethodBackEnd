"""
Zamanlanmış bildirim gönderimi.
run_worker komutu tarafından her 10 dakikada bir çağrılır.
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
        from accounts.models import PatientProfile
        # Kişiye özel su hedefine ulaşmış olanları çıkar
        reached = set()
        for log in DailyWaterLog.objects.filter(date=today).select_related("patient"):
            profile = PatientProfile.objects.filter(user=log.patient).first()
            goal = profile.daily_water_goal_ml if profile else 2000
            if log.ml_consumed >= goal:
                reached.add(log.patient_id)
        return [p for p in patients if p.id not in reached]

    elif notification_type == "steps":
        logged = set(
            DailyStepLog.objects.filter(date=today, step_count__gt=0)
            .values_list("patient_id", flat=True)
        )
        return [p for p in patients if p.id not in logged]

    elif notification_type == "exercise":
        has_active = set(
            ExerciseAssignment.objects.filter(is_active=True)
            .values_list("patient_id", flat=True)
        )
        from wellness.models import ExerciseCompletion
        completed_today = set(
            ExerciseCompletion.objects.filter(completed_at__date=today)
            .values_list("patient_id", flat=True)
        )
        target_ids = has_active - completed_today
        return [p for p in patients if p.id in target_ids]

    else:
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
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force-id", type=int)

    def handle(self, *args, **options):
        from wellness.models import NotificationSchedule
        from accounts.push_service import send_push_to_users

        dry_run = options["dry_run"]
        force_id = options.get("force_id")

        now = timezone.localtime()
        today = timezone.localdate()
        today_str = str(today)
        window = timedelta(minutes=10)

        qs = NotificationSchedule.objects.filter(is_enabled=True)
        if force_id:
            qs = NotificationSchedule.objects.filter(pk=force_id)

        fired = 0
        for schedule in qs:
            send_times = schedule.send_times or []
            last_triggered = schedule.last_triggered_times or {}

            for send_time_str in send_times:
                key = f"{today_str}:{send_time_str}"

                if not force_id:
                    # Gün kontrolü
                    if today.weekday() not in (schedule.days_of_week or []):
                        continue
                    # Zaman penceresi kontrolü
                    try:
                        h, m = map(int, send_time_str.split(":"))
                        scheduled_dt = timezone.make_aware(
                            datetime.combine(today, datetime.min.time().replace(hour=h, minute=m))
                        )
                    except (ValueError, AttributeError):
                        continue
                    if abs((now - scheduled_dt).total_seconds()) > window.total_seconds():
                        continue
                    # Bugün bu saat zaten gönderildi mi?
                    if last_triggered.get(key):
                        continue

                users = _get_target_users(schedule.notification_type)
                link = LINK_MAP.get(schedule.notification_type, "/hesabim")

                if dry_run:
                    self.stdout.write(
                        f"[DRY-RUN] Schedule #{schedule.id} saat {send_time_str} "
                        f"→ {len(users)} kullanıcı"
                    )
                else:
                    if users:
                        send_push_to_users(
                            users,
                            title=schedule.title,
                            body=schedule.message,
                            data={"link": link, "notification_type": schedule.notification_type},
                        )

                    if not force_id:
                        last_triggered[key] = True
                        # 7 günden eski kayıtları temizle (şişme önleme)
                        cutoff = str(today - timedelta(days=7))
                        last_triggered = {k: v for k, v in last_triggered.items() if k[:10] >= cutoff}
                        schedule.last_triggered_times = last_triggered
                        schedule.save(update_fields=["last_triggered_times", "updated_at"])

                    fired += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Schedule #{schedule.id} saat {send_time_str} gönderildi → {len(users)} kullanıcı"
                        )
                    )

        if fired == 0 and not dry_run and not force_id:
            self.stdout.write("Bu çalışmada gönderilecek schedule bulunamadı.")
