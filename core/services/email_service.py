from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_html_email(subject, to_emails, html_template, text_template=None, context=None):
    context = context or {}

    html_body = render_to_string(html_template, context)

    if text_template:
        text_body = render_to_string(text_template, context)
    else:
        text_body = "يرجى عرض هذه الرسالة في بريد يدعم HTML."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_emails,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()
