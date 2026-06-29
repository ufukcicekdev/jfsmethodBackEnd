"""
Bildirim worker'ı — ROLE=worker servisinde çalışır.
Her 10 dakikada fire_scheduled_notifications komutunu tetikler.
Railway servisi restart edince otomatik yeniden başlar.
"""

import logging
import time

from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 10 * 60  # 10 dakika


class Command(BaseCommand):
    help = "Zamanlanmış bildirimleri arka planda döngüsel olarak çalıştırır (ROLE=worker)."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f"Worker başladı. Her {INTERVAL_SECONDS // 60} dakikada kontrol edilecek."
            )
        )

        while True:
            try:
                call_command("fire_scheduled_notifications")
            except Exception as exc:
                logger.exception("fire_scheduled_notifications hatası: %s", exc)
                self.stderr.write(f"Hata (devam ediliyor): {exc}")
            finally:
                # Her turdan sonra Django ORM query cache'ini temizle
                from django import db
                db.reset_queries()
                db.close_old_connections()

            self.stdout.write(f"Sonraki kontrol {INTERVAL_SECONDS // 60} dakika sonra.")
            time.sleep(INTERVAL_SECONDS)
