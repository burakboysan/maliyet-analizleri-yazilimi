import smtplib
from email.message import EmailMessage
from email.utils import formataddr


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "noreplybomaksan@gmail.com"
SMTP_PASSWORD = None  # VM uzerinde ortam degiskeninden okunacak
SMTP_FROM_EMAIL = "noreplybomaksan@gmail.com"
SMTP_USE_TLS = True

RECIPIENTS = [
    "beyzanurapaydin@bomaksan.com",
    "boraboysan@bomaksan.com",
    "burakboysan@bomaksan.com",
    "hakancaresiz@bomaksan.com",
    "sametbor@bomaksan.com",
    "zaferdeliomeroglu@bomaksan.com",
]

SUBJECT = "Bomaksan Maliyet Analizleri sertifika kurulum paketi"
DOWNLOAD_URL = "https://storage.googleapis.com/maliyet-analizi-yazilimi-updates-416688102123/internal/internal_signer_package.zip"

BODY = f"""Merhaba,

Bomaksan Maliyet Analizleri yaziliminin guncellemelerini sorunsuz alabilmeniz icin once sertifika kurulum paketini yuklemeniz gerekiyor.

Indirme baglantisi:
{DOWNLOAD_URL}

Lutfen zip dosyasini indirip acin ve klasor icindeki install_internal_signer.bat dosyasina cift tiklayin.

Bu islem tek seferliktir.

Tesekkurler.
"""

HTML_BODY = f"""
<html>
  <body style="margin:0;padding:24px;background:#f5f5f5;font-family:Arial,sans-serif;color:#222;">
    <div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e5e5e5;border-radius:12px;padding:32px;">
      <div style="font-size:20px;font-weight:700;color:#b71c1c;margin-bottom:20px;">Bomaksan Maliyet Analizleri</div>
      <p>Merhaba,</p>
      <p>Yazilimin guncellemelerini sorunsuz alabilmeniz icin once sertifika kurulum paketini yuklemeniz gerekiyor.</p>
      <p><a href="{DOWNLOAD_URL}">{DOWNLOAD_URL}</a></p>
      <p>Lutfen zip dosyasini indirip acin ve klasor icindeki <strong>install_internal_signer.bat</strong> dosyasina cift tiklayin.</p>
      <p>Bu islem tek seferliktir.</p>
      <p>Tesekkurler.</p>
    </div>
  </body>
</html>
"""


def send_email(password: str, to_email: str) -> None:
    message = EmailMessage()
    message["Subject"] = SUBJECT
    message["From"] = formataddr(("Bomaksan Maliyet Analizleri", SMTP_FROM_EMAIL))
    message["To"] = to_email
    message.set_content(BODY)
    message.add_alternative(HTML_BODY, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        if SMTP_USE_TLS:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(SMTP_USERNAME, password)
        smtp.send_message(message)


if __name__ == "__main__":
    import os

    password = os.getenv("SMTP_PASSWORD", "").strip()
    if not password:
        raise SystemExit("SMTP_PASSWORD bulunamadi.")

    for recipient in RECIPIENTS:
        send_email(password, recipient)
        print(f"SENT {recipient}")
