from django.conf import settings
from django.db import models


class ConsentType(models.TextChoices):
    AYDINLATMA_METNI = "AYDINLATMA_METNI", "Aydınlatma Metni"
    ACIK_RIZA_SAGLIK = "ACIK_RIZA_SAGLIK", "Açık Rıza — Sağlık Verileri"
    COOKIE_ESSENTIAL = "COOKIE_ESSENTIAL", "Zorunlu Çerezler"
    COOKIE_ANALYTICS = "COOKIE_ANALYTICS", "Analitik Çerezler"
    COOKIE_MARKETING = "COOKIE_MARKETING", "Pazarlama Çerezleri"


class KVKKConsentLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kvkk_consents",
    )
    consent_type = models.CharField(max_length=32, choices=ConsentType.choices)
    is_accepted = models.BooleanField()
    kvkk_version = models.CharField(max_length=16, default="v1.0")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "KVKK Consent Log"
        verbose_name_plural = "KVKK Consent Logs"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "consent_type"]),
            models.Index(fields=["consent_type", "timestamp"]),
        ]

    def __str__(self):
        user_label = self.user.username if self.user else "anonim"
        status = "kabul" if self.is_accepted else "red"
        return f"{user_label} — {self.consent_type} ({status}) @ {self.timestamp:%Y-%m-%d %H:%M}"
