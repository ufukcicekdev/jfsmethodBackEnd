"""Gün sonu katılım işaretleme hatırlatması — cron ile çalıştırılır (örn. her gün 20:00)."""
from django.core.management.base import BaseCommand

from appointments.reminder_service import send_eod_attendance_reminders


class Command(BaseCommand):
    help = "Bugünkü katılım işaretlenmemiş randevular için admine push gönderir."

    def handle(self, *args, **options):
        result = send_eod_attendance_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Gün sonu hatırlatma tamamlandı: {result['notified']} randevu"
            )
        )
