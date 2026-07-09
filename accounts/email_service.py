import logging
import os
import threading

from django.conf import settings

logger = logging.getLogger(__name__)

SITE_NAME = "JFS Method"
SITE_URL = "https://jfsmethod.com"


def _base(title: str, preview: str, content: str) -> str:
    """Email-safe HTML — tüm stiller inline, gradient yok, tablo layout."""
    return f"""<!DOCTYPE html>
<html lang="tr" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta http-equiv="X-UA-Compatible" content="IE=edge"/>
<title>{title}</title>
<meta name="color-scheme" content="light"/>
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#f0f4f8;-webkit-text-size-adjust:100%;mso-line-height-rule:exactly;">

<!-- Preview text -->
<div style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#f0f4f8;">{preview}</div>

<!-- Wrapper -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;">
  <tr>
    <td align="center" style="padding:40px 16px;">

      <!-- Card -->
      <table role="presentation" width="100%" style="max-width:560px;" cellpadding="0" cellspacing="0">

        <!-- Header -->
        <tr>
          <td style="background-color:#0f172a;border-radius:16px 16px 0 0;padding:0;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="padding:36px 48px 32px;">
                  <!-- Logo area -->
                  <table role="presentation" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="vertical-align:middle;">
                        <img src="https://fra1.digitaloceanspaces.com/cekfisi/static/icon-192.png" alt="JFS Method" width="44" height="44" style="display:block;border-radius:10px;border:0;"/>
                      </td>
                      <td style="padding-left:12px;vertical-align:middle;">
                        <span style="color:#ffffff;font-size:18px;font-weight:700;font-family:Arial,sans-serif;letter-spacing:-0.3px;">JFS Method</span>
                      </td>
                    </tr>
                  </table>
                  <!-- Divider -->
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding-top:24px;">
                        <div style="height:1px;background-color:#1e293b;font-size:0;line-height:0;">&nbsp;</div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="background-color:#ffffff;padding:40px 48px;">
            {content}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background-color:#f8fafc;border-radius:0 0 16px 16px;border-top:1px solid #e2e8f0;padding:24px 48px;text-align:center;">
            <p style="margin:0;font-family:Arial,sans-serif;font-size:12px;color:#94a3b8;line-height:1.6;">
              Bu e-posta {SITE_NAME} tarafından otomatik gönderilmiştir.<br/>
              <a href="{SITE_URL}" style="color:#64748b;text-decoration:none;">{SITE_URL}</a>
            </p>
          </td>
        </tr>

      </table>
      <!-- /Card -->

    </td>
  </tr>
</table>

</body>
</html>"""


def _cred_box(label: str, value: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
      <tr>
        <td style="background-color:#f8fafc;border:1px solid #e2e8f0;border-left:3px solid #2563eb;border-radius:8px;padding:14px 18px;">
          <p style="margin:0 0 3px;font-family:Arial,sans-serif;font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;text-transform:uppercase;">{label}</p>
          <p style="margin:0;font-family:'Courier New',Courier,monospace;font-size:16px;font-weight:700;color:#0f172a;">{value}</p>
        </td>
      </tr>
    </table>"""


def _btn(text: str, url: str) -> str:
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" style="margin:32px 0 0;">
      <tr>
        <td style="background-color:#2563eb;border-radius:50px;">
          <a href="{url}" style="display:inline-block;padding:14px 36px;font-family:Arial,sans-serif;font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;letter-spacing:0.2px;">{text}</a>
        </td>
      </tr>
    </table>"""


def _alert(text: str, color: str = "#1e40af", bg: str = "#eff6ff", border: str = "#bfdbfe") -> str:
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:28px;">
      <tr>
        <td style="background-color:{bg};border:1px solid {border};border-radius:10px;padding:14px 18px;">
          <p style="margin:0;font-family:Arial,sans-serif;font-size:13px;color:{color};line-height:1.6;">{text}</p>
        </td>
      </tr>
    </table>"""


def send_welcome_email(user, plain_password: str):
    if not user.email:
        return
    full_name = user.get_full_name() or user.username
    subject = f"{SITE_NAME} — Hesabınız Hazır"

    plain = (
        f"Merhaba {full_name},\n\n"
        f"JFS Method platformuna hoş geldiniz!\n\n"
        f"Giriş bilgileriniz:\n"
        f"  Kullanıcı adı : {user.username}\n"
        f"  Şifre         : {plain_password}\n\n"
        f"Giriş: {SITE_URL}/giris\n\n"
        f"İlk girişinizde şifrenizi değiştirmenizi öneririz.\n\n"
        f"{SITE_NAME}"
    )

    content = f"""
      <h1 style="margin:0 0 6px;font-family:Arial,sans-serif;font-size:24px;font-weight:800;color:#0f172a;letter-spacing:-0.5px;">Hesabınız hazır 🎉</h1>
      <p style="margin:0 0 32px;font-family:Arial,sans-serif;font-size:15px;color:#64748b;line-height:1.7;">
        Merhaba <strong style="color:#0f172a;">{full_name}</strong>,<br/>
        JFS Method programına hoş geldiniz. Aşağıdaki bilgilerle platforma giriş yapabilirsiniz.
      </p>

      {_cred_box("Kullanıcı Adı", user.username)}
      {_cred_box("Şifre", plain_password)}

      {_btn("Platforma Giriş Yap", f"{SITE_URL}/giris")}

      {_alert("🔒 &nbsp;<strong>Güvenlik:</strong> İlk girişinizde şifrenizi değiştirmenizi öneririz. Profil sayfanızdan kolayca güncelleyebilirsiniz.")}
    """

    _send_async(subject, plain, _base(subject, f"Merhaba {full_name}, giriş bilgileriniz hazır.", content), [user.email])


def send_password_reset_email(user, reset_url: str):
    if not user.email:
        return
    full_name = user.get_full_name() or user.username
    subject = f"{SITE_NAME} — Şifre Sıfırlama"

    plain = (
        f"Merhaba {full_name},\n\n"
        f"Şifrenizi sıfırlamak için:\n{reset_url}\n\n"
        f"Bu bağlantı sınırlı süre geçerlidir.\n"
        f"Bu isteği siz yapmadıysanız görmezden gelebilirsiniz.\n\n"
        f"{SITE_NAME}"
    )

    content = f"""
      <h1 style="margin:0 0 6px;font-family:Arial,sans-serif;font-size:24px;font-weight:800;color:#0f172a;letter-spacing:-0.5px;">Şifre sıfırlama</h1>
      <p style="margin:0 0 32px;font-family:Arial,sans-serif;font-size:15px;color:#64748b;line-height:1.7;">
        Merhaba <strong style="color:#0f172a;">{full_name}</strong>,<br/>
        Hesabınız için şifre sıfırlama talebi aldık. Aşağıdaki butona tıklayarak yeni şifrenizi belirleyebilirsiniz.
      </p>

      {_btn("Şifremi Sıfırla", reset_url)}

      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:24px;">
        <tr>
          <td style="padding-top:24px;border-top:1px solid #f1f5f9;">
            <p style="margin:0 0 6px;font-family:Arial,sans-serif;font-size:12px;color:#94a3b8;">Buton çalışmıyorsa bu adresi tarayıcınıza kopyalayın:</p>
            <p style="margin:0;font-family:'Courier New',Courier,monospace;font-size:11px;color:#64748b;word-break:break-all;">{reset_url}</p>
          </td>
        </tr>
      </table>

      {_alert("⚠️ &nbsp;Bu talebi siz yapmadıysanız bu e-postayı güvenle silebilirsiniz. Hesabınızda herhangi bir değişiklik yapılmadı.", color="#92400e", bg="#fffbeb", border="#fde68a")}
    """

    _send_async(subject, plain, _base(subject, "Şifrenizi sıfırlamak için bağlantınız hazır.", content), [user.email])


def send_password_changed_by_admin_email(user, admin_name: str = ""):
    if not user.email:
        return
    full_name = user.get_full_name() or user.username
    subject = f"{SITE_NAME} — Şifreniz Güncellendi"
    by = f" <strong style='color:#0f172a;'>{admin_name}</strong> tarafından" if admin_name else " danışmanınız tarafından"
    by_plain = f" {admin_name} tarafından" if admin_name else " danışmanınız tarafından"

    plain = (
        f"Merhaba {full_name},\n\n"
        f"Hesabınızın şifresi{by_plain} güncellendi.\n"
        f"Yeni şifrenizle giriş yapabilirsiniz: {SITE_URL}/giris\n\n"
        f"Bu değişikliği siz talep etmediyseniz lütfen danışmanınızla iletişime geçin.\n\n"
        f"{SITE_NAME}"
    )

    content = f"""
      <h1 style="margin:0 0 6px;font-family:Arial,sans-serif;font-size:24px;font-weight:800;color:#0f172a;letter-spacing:-0.5px;">Şifreniz güncellendi</h1>
      <p style="margin:0 0 32px;font-family:Arial,sans-serif;font-size:15px;color:#64748b;line-height:1.7;">
        Merhaba <strong style="color:#0f172a;">{full_name}</strong>,<br/>
        Hesabınızın şifresi{by} güncellendi. Yeni şifrenizle platforma giriş yapabilirsiniz.
      </p>

      {_btn("Platforma Giriş Yap", f"{SITE_URL}/giris")}

      {_alert("⚠️ &nbsp;Bu değişikliği siz talep etmediyseniz lütfen danışmanınızla iletişime geçin.", color="#991b1b", bg="#fef2f2", border="#fecaca")}
    """

    _send_async(subject, plain, _base(subject, f"Hesabınızın şifresi güncellendi.", content), [user.email])


def _send_async(subject: str, plain: str, html: str, recipients: list[str]):
    def _send():
        try:
            import urllib.request, json as _json
            api_key = os.environ.get("SMTP2GO_API_KEY", "")
            sender = settings.DEFAULT_FROM_EMAIL
            payload = _json.dumps({
                "api_key": api_key,
                "to": recipients,
                "sender": sender,
                "subject": subject,
                "text_body": plain,
                "html_body": html,
            }).encode()
            req = urllib.request.Request(
                "https://api.smtp2go.com/v3/email/send",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                logger.info("SMTP2GO: %s", resp.read().decode())
        except Exception:
            logger.exception("Email send failed to %s", recipients)

    threading.Thread(target=_send, daemon=True).start()
