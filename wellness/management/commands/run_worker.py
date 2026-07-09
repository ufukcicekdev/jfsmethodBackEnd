"""
Bildirim worker'ı — ROLE=worker servisinde çalışır.
Her 10 dakikada fire_scheduled_notifications komutunu tetikler.
3 günde bir generate_scheduled_blogs komutunu tetikler.
Railway servisi restart edince otomatik yeniden başlar.
"""

import logging
import time
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

INTERVAL_SECONDS = 10 * 60  # 10 dakika
BLOG_INTERVAL_DAYS = 3


def _should_generate_blogs():
    """Son başarılı blog üretiminden BLOG_INTERVAL_DAYS gün geçtiyse True döner."""
    from django.utils import timezone
    from blog.models import BlogPost

    last = BlogPost.objects.filter(ai_generated=True).order_by("-created_at").first()
    if last is None:
        return True
    return timezone.now() - last.created_at >= timedelta(days=BLOG_INTERVAL_DAYS)


class Command(BaseCommand):
    help = "Zamanlanmış bildirimleri ve blog üretimini arka planda döngüsel olarak çalıştırır (ROLE=worker)."

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f"Worker başladı. Her {INTERVAL_SECONDS // 60} dakikada kontrol edilecek."
            )
        )

        while True:
            # Bildirimler
            try:
                call_command("fire_scheduled_notifications")
            except Exception as exc:
                logger.exception("fire_scheduled_notifications hatası: %s", exc)
                self.stderr.write(f"Hata (devam ediliyor): {exc}")

            # Blog üretimi — 3 günde bir
            try:
                if _should_generate_blogs():
                    self.stdout.write("Blog üretimi tetikleniyor…")
                    call_command("generate_scheduled_blogs")
            except Exception as exc:
                logger.exception("generate_scheduled_blogs hatası: %s", exc)
                self.stderr.write(f"Blog üretimi hatası (devam ediliyor): {exc}")
            finally:
                from django import db
                db.reset_queries()
                db.close_old_connections()

            self.stdout.write(f"Sonraki kontrol {INTERVAL_SECONDS // 60} dakika sonra.")
            time.sleep(INTERVAL_SECONDS)
