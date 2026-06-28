from rest_framework import serializers

from .constants import KVKK_POLICY_VERSION
from .models import ConsentType


class ConsentItemSerializer(serializers.Serializer):
    consent_type = serializers.ChoiceField(choices=ConsentType.choices)
    is_accepted = serializers.BooleanField()
    kvkk_version = serializers.CharField(default=KVKK_POLICY_VERSION, required=False)


class CookieConsentSerializer(serializers.Serializer):
    analytics = serializers.BooleanField()
    marketing = serializers.BooleanField()
    kvkk_version = serializers.CharField(default=KVKK_POLICY_VERSION, required=False)

    def to_consent_items(self):
        version = self.validated_data.get("kvkk_version", KVKK_POLICY_VERSION)
        return [
            {
                "consent_type": ConsentType.COOKIE_ESSENTIAL,
                "is_accepted": True,
                "kvkk_version": version,
            },
            {
                "consent_type": ConsentType.COOKIE_ANALYTICS,
                "is_accepted": self.validated_data["analytics"],
                "kvkk_version": version,
            },
            {
                "consent_type": ConsentType.COOKIE_MARKETING,
                "is_accepted": self.validated_data["marketing"],
                "kvkk_version": version,
            },
        ]
