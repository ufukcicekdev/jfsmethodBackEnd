"""Yaklaşan randevular için hatırlatma bildirimi gönderen komut.

Periyodik çalıştırılmak üzere tasarlandı (örn. cron ile her 10 dakikada bir):

    */10 * * * * cd /path/to/backend && /path/to/venv/bin/python \
        manage.py send_appointment_reminders >> /var/log/fizyotech_reminders.log 2>&1
"""

from django.core.management.base import BaseCommand

from appointments.reminder_service import send_due_reminders


class Command(BaseCommand):
    help = "Zamanı yaklaşan randevular için hatırlatma push bildirimi gönderir."

    def handle(self, *args, **options):
        result = send_due_reminders()
        self.stdout.write(
            self.style.SUCCESS(
                f"Hatırlatmalar gönderildi: "
                f"24 saat={result['sent_24h']}, 1 saat={result['sent_1h']}"
            )
        )
