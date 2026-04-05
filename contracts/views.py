import base64
import os
from io import BytesIO

import arabic_reshaper
import qrcode
from bidi.algorithm import get_display
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from hijridate import Gregorian
from weasyprint import HTML

from core.models import User
from .forms import MaintenanceContractForm, ContractClauseTemplateForm
from .models import ContractClauseTemplate, MaintenanceContract, MaintenanceContractClause


ARABIC_HIJRI_MONTHS = {
    1: "محرم",
    2: "صفر",
    3: "ربيع الأول",
    4: "ربيع الآخر",
    5: "جمادى الأولى",
    6: "جمادى الآخرة",
    7: "رجب",
    8: "شعبان",
    9: "رمضان",
    10: "شوال",
    11: "ذو القعدة",
    12: "ذو الحجة",
}


def format_hijri(date_obj):
    if not date_obj:
        return "-"
    hijri = Gregorian(date_obj.year, date_obj.month, date_obj.day).to_hijri()
    month_name = ARABIC_HIJRI_MONTHS.get(hijri.month, str(hijri.month))
    return f"{hijri.day} {month_name} {hijri.year}هـ"


def build_qr_code_base64(data):
    if not data:
        return ""

    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


def send_html_email(subject, to_emails, html_template, text_template=None, context=None):
    context = context or {}

    if not to_emails:
        return

    html_body = render_to_string(html_template, context)
    text_body = render_to_string(text_template, context) if text_template else "رسالة من منصة وقاية"

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_emails,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()


# -----------------------------
# صلاحيات
# -----------------------------
def is_client(user):
    return user.is_authenticated and user.user_type == "client"


def can_manage_contracts(user):
    return user.is_authenticated and user.user_type in ["executive", "admin_assistant"]


def get_user_institution(user):
    return user.institutions.first()


def get_contract_for_user_or_404(user, contract_id):
    institution = get_user_institution(user)

    qs = MaintenanceContract.objects.select_related("client", "institution", "executive")

    if is_client(user):
        return get_object_or_404(qs, id=contract_id, client=user)

    if can_manage_contracts(user):
        return get_object_or_404(qs, id=contract_id, institution=institution)

    raise HttpResponseForbidden("غير مصرح لك")


# -----------------------------
# عرض العقود
# -----------------------------
@login_required
def contract_list_view(request):
    institution = get_user_institution(request.user)

    if can_manage_contracts(request.user):
        contracts = MaintenanceContract.objects.filter(institution=institution)
    elif is_client(request.user):
        contracts = MaintenanceContract.objects.filter(client=request.user)
    else:
        return HttpResponseForbidden()

    return render(request, "contracts/contract_list.html", {"contracts": contracts})


# -----------------------------
# إنشاء عقد
# -----------------------------
@login_required
def contract_create_view(request):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden()

    institution = get_user_institution(request.user)
    form = MaintenanceContractForm(request.POST or None, institution=institution)

    if form.is_valid():
        contract = form.save(commit=False)
        contract.institution = institution
        contract.executive = request.user
        contract.save()

        messages.success(request, "تم إنشاء العقد")
        return redirect("contracts_list")

    return render(request, "contracts/contract_form.html", {"form": form})


# -----------------------------
# تفاصيل
# -----------------------------
@login_required
def contract_detail_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)
    return render(request, "contracts/contract_detail.html", {"contract": contract})


# -----------------------------
# طباعة
# -----------------------------
@login_required
def contract_print_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    context = {
        "contract": contract,
        "created_at_hijri": format_hijri(contract.created_at.date()),
        "start_date_hijri": format_hijri(contract.start_date),
        "end_date_hijri": format_hijri(contract.end_date),
    }

    return render(request, "contracts/contract_print.html", context)


# -----------------------------
# تحميل PDF (نفس الطباعة)
# -----------------------------
@login_required
def contract_download_pdf_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    context = {
        "contract": contract,
        "created_at_hijri": format_hijri(contract.created_at.date()),
        "start_date_hijri": format_hijri(contract.start_date),
        "end_date_hijri": format_hijri(contract.end_date),
    }

    html_string = render_to_string("contracts/contract_print.html", context)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="contract_{contract.contract_number}.pdf"'

    try:
        HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf(response)
    except Exception:
        messages.error(request, "خطأ في إنشاء PDF")
        return redirect("contract_detail", contract_id=contract.id)

    return response


# -----------------------------
# حذف
# -----------------------------
@login_required
def contract_delete_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    if request.method == "POST":
        contract.delete()
        messages.success(request, "تم الحذف")
        return redirect("contracts_list")

    return render(request, "contracts/contract_confirm_delete.html", {"contract": contract})
