"""Firebase Cloud Messaging (FCM) push notification service.

Firebase yapılandırması (kimlik bilgileri dosyası) ortam değişkeni ile
sağlanır. Yapılandırma yoksa veya firebase-admin paketi kurulu değilse
gönderimler sessizce atlanır; uygulama bundan etkilenmez.

Ortam değişkeni:
    FIREBASE_CREDENTIALS_PATH -> service account JSON dosyasının yolu
    (Firebase Console > Project Settings > Service accounts > Generate new
    private key ile indirilir.)
"""

import logging
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

_init_lock = threading.Lock()
_init_done = False
_messaging = None


def _ensure_initialized():
    """firebase-admin uygulamasını bir kez başlatır. Hazırsa True döner."""
    global _init_done, _messaging

    if _init_done:
        return _messaging is not None

    with _init_lock:
        if _init_done:
            return _messaging is not None
        _init_done = True

        import json, os

        try:
            import firebase_admin
            from firebase_admin import credentials, messaging
        except ImportError:
            logger.warning("FCM devre dışı: 'firebase-admin' paketi kurulu değil.")
            return False

        # Önce JSON string env var'ına bak, sonra dosya yoluna
        cred_json = os.environ.get("FIREBASE_CREDENTIALS_JSON", "")
        cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "") or ""

        try:
            if not firebase_admin._apps:
                if cred_json:
                    cred_dict = json.loads(cred_json)
                    firebase_admin.initialize_app(credentials.Certificate(cred_dict))
                elif cred_path and os.path.exists(cred_path):
                    firebase_admin.initialize_app(credentials.Certificate(cred_path))
                else:
                    logger.info("FCM devre dışı: FIREBASE_CREDENTIALS_JSON veya FIREBASE_CREDENTIALS_PATH ayarlı değil.")
                    return False
            _messaging = messaging
            logger.info("FCM başlatıldı.")
            return True
        except Exception:
            logger.exception("FCM başlatılamadı.")
            return False


def _send_now(tokens, title, body, data):
    messaging = _messaging
    if messaging is None:
        return

    from accounts.models import FCMDevice

    payload_data = {k: str(v) for k, v in (data or {}).items()}

    invalid_tokens = []
    for token in tokens:
        message = messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=payload_data,
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon="/icon-192.png",
                ),
                fcm_options=messaging.WebpushFCMOptions(
                    link=payload_data.get("link", "/"),
                ),
            ),
        )
        try:
            messaging.send(message)
        except Exception as exc:  # noqa: BLE001
            name = exc.__class__.__name__
            if name in {
                "UnregisteredError",
                "SenderIdMismatchError",
                "InvalidArgumentError",
            }:
                invalid_tokens.append(token)
            else:
                logger.warning("FCM gönderimi başarısız (%s): %s", name, exc)

    if invalid_tokens:
        FCMDevice.objects.filter(token__in=invalid_tokens).update(is_active=False)


def send_push_to_users(users, *, title, body, data=None):
    """Verilen kullanıcı(lar)ın aktif cihazlarına push bildirimi gönderir.

    Gönderim arka planda yapılır, çağıran isteği bloklamaz.
    """
    if not _ensure_initialized():
        return

    from accounts.models import FCMDevice

    if not isinstance(users, (list, tuple, set)):
        users = [users]
    user_ids = [u.id if hasattr(u, "id") else u for u in users if u]
    if not user_ids:
        return

    link = (data or {}).get("link", "/hesabim")
    notification_type = (data or {}).get("notification_type", "general")
    try:
        from accounts.patient_notification_service import (
            create_patient_notifications_for_users,
        )

        create_patient_notifications_for_users(
            user_ids,
            notification_type=notification_type,
            title=title,
            message=body,
            link=link,
        )
    except Exception:
        logger.exception("In-app patient notification creation failed")

    tokens = list(
        FCMDevice.objects.filter(
            user_id__in=user_ids, is_active=True
        ).values_list("token", flat=True)
    )
    if not tokens:
        return

    thread = threading.Thread(
        target=_send_now,
        args=(tokens, title, body, data),
        daemon=True,
    )
    thread.start()


def send_push_to_staff(*, title, body, data=None):
    """Tüm aktif personel (admin/doktor) kullanıcılarına push gönderir."""
    from django.contrib.auth.models import User

    staff = list(User.objects.filter(is_staff=True, is_active=True))
    send_push_to_users(staff, title=title, body=body, data=data)
