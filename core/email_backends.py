from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class SendGridAPIEmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = getattr(settings, "SENDGRID_API_KEY", "")
        self.default_from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "")

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            raise ValueError("SENDGRID_API_KEY غير مضبوط")

        client = SendGridAPIClient(self.api_key)
        sent_count = 0

        for message in email_messages:
            from_email = message.from_email or self.default_from_email
            if not from_email:
                raise ValueError("DEFAULT_FROM_EMAIL غير مضبوط")

            plain_body = message.body or ""
            html_body = None

            for alt in getattr(message, "alternatives", []):
                if len(alt) >= 2 and alt[1] == "text/html":
                    html_body = alt[0]
                    break

            mail = Mail(
                from_email=sanitize_address(from_email, "utf-8"),
                to_emails=[sanitize_address(addr, "utf-8") for addr in message.to],
                subject=message.subject or "",
                plain_text_content=plain_body,
                html_content=html_body,
            )

            if message.cc:
                for cc_email in message.cc:
                    mail.add_cc(sanitize_address(cc_email, "utf-8"))

            if message.bcc:
                for bcc_email in message.bcc:
                    mail.add_bcc(sanitize_address(bcc_email, "utf-8"))

            reply_to = getattr(message, "reply_to", None)
            if reply_to:
                mail.reply_to = sanitize_address(reply_to[0], "utf-8")

            response = client.send(mail)
            print("SENDGRID STATUS:", response.status_code)
            print("SENDGRID BODY:", response.body)
            print("SENDGRID HEADERS:", response.headers)

            if response.status_code in (200, 201, 202):
                sent_count += 1
            else:
                raise RuntimeError(
                    f"فشل الإرسال عبر SendGrid: "
                    f"status={response.status_code}, body={response.body}"
                )

        return sent_count
