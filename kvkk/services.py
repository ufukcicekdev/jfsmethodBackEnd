from django.db import transaction

from .constants import KVKK_POLICY_VERSION
from .models import ConsentType, KVKKConsentLog
from .utils import get_client_ip, get_user_agent


def log_consent(
    request,
    consent_type: str,
    is_accepted: bool,
    user=None,
    kvkk_version: str = KVKK_POLICY_VERSION,
) -> KVKKConsentLog:
    return KVKKConsentLog.objects.create(
        user=user,
        consent_type=consent_type,
        is_accepted=is_accepted,
        kvkk_version=kvkk_version,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )


@transaction.atomic
def log_consents(
    request,
    consents: list[dict],
    user=None,
    kvkk_version: str = KVKK_POLICY_VERSION,
) -> list[KVKKConsentLog]:
    logs = []
    for item in consents:
        consent_type = item["consent_type"]
        if consent_type not in ConsentType.values:
            raise ValueError(f"Invalid consent type: {consent_type}")
        logs.append(
            log_consent(
                request=request,
                consent_type=consent_type,
                is_accepted=item["is_accepted"],
                user=user,
                kvkk_version=item.get("kvkk_version", kvkk_version),
            )
        )
    return logs


def log_registration_consents(request, user, kvkk_accepted: bool, acik_riza_accepted: bool):
    log_consents(
        request,
        [
            {"consent_type": ConsentType.AYDINLATMA_METNI, "is_accepted": kvkk_accepted},
            {"consent_type": ConsentType.ACIK_RIZA_SAGLIK, "is_accepted": acik_riza_accepted},
        ],
        user=user,
    )


def log_appointment_consents(request, user, kvkk_accepted: bool, acik_riza_accepted: bool):
    log_consents(
        request,
        [
            {"consent_type": ConsentType.AYDINLATMA_METNI, "is_accepted": kvkk_accepted},
            {"consent_type": ConsentType.ACIK_RIZA_SAGLIK, "is_accepted": acik_riza_accepted},
        ],
        user=user,
    )
