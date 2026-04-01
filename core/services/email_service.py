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
    def send_contract_created_email(user, contract, action_url):
    if not user.email:
        return

    send_html_email(
        subject="تم إنشاء عقد صيانة جديد | منصة وقاية",
        to_emails=[user.email],
        html_template="emails/contract_created.html",
        text_template="emails/contract_created.txt",
        context={
            "client_name": user.get_display_name(),
            "contract_number": contract.contract_number,
            "building_name": contract.building_name,
            "building_location": contract.building_location,
            "action_url": action_url,
        },
    )
