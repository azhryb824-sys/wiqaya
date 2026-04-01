from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class SendGridAPIEmailBackend(BaseEmailBackend):
    """
    Email backend يستخدم SendGrid Web API بدل SMTP.
    مناسب لـ Railway لأن الإرسال يتم عبر HTTPS.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = getattr(settings, "SENDGRID_API_KEY", "")
        self.default_from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            if not self.fail_silently:
                raise ValueError("SENDGRID_API_KEY غير مضبوط في الإعدادات")
            return 0

        client = SendGridAPIClient(self.api_key)
        sent_count = 0

        for message in email_messages:
            try:
                from_email = message.from_email or self.default_from_email
                if not from_email:
                    raise ValueError("لا يوجد بريد مرسل from_email أو DEFAULT_FROM_EMAIL")

                # محتوى الرسالة
                plain_body = message.body or ""
                html_body = None
                for alt in getattr(message, "alternatives", []):
                    if len(alt) >= 2 and alt[1] == "text/html":
                        html_body = alt[0]
                        break

                # إنشاء الرسالة
                mail = Mail(
                    from_email=sanitize_address(from_email, "utf-8"),
                    to_emails=[sanitize_address(addr, "utf-8") for addr in message.to],
                    subject=message.subject or "",
                    plain_text_content=plain_body,
                    html_content=html_body,
                )

                # CC
                if message.cc:
                    for cc_email in message.cc:
                        mail.add_cc(sanitize_address(cc_email, "utf-8"))

                # BCC
                if message.bcc:
                    for bcc_email in message.bcc:
                        mail.add_bcc(sanitize_address(bcc_email, "utf-8"))

                # Reply-To
                reply_to = getattr(message, "reply_to", None)
                if reply_to:
                    mail.reply_to = sanitize_address(reply_to[0], "utf-8")

                response = client.send(mail)

                # SendGrid Mail Send API يرجع 202 عند قبول الطلب غالبًا
                if response.status_code in (200, 201, 202):
                    sent_count += 1
                elif not self.fail_silently:
                    raise RuntimeError(
                        f"فشل إرسال البريد عبر SendGrid. "
                        f"status={response.status_code}, body={response.body}"
                    )

            except Exception:
                if not self.fail_silently:
                    raise

        return sent_count
