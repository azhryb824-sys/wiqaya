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

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_RIGHT

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
# تعديل عقد
# -----------------------------
@login_required
def contract_edit_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    if request.user.user_type not in ["executive", "admin_assistant"]:
        return HttpResponseForbidden("غير مصرح لك")

    institution = get_user_institution(request.user)

    form = MaintenanceContractForm(
        request.POST or None,
        instance=contract,
        institution=institution,
    )

    if request.method == "POST":
        if form.is_valid():
            updated_contract = form.save(commit=False)
            updated_contract.institution = institution
            updated_contract.executive = request.user
            updated_contract.save()

            messages.success(request, "تم تعديل العقد بنجاح")
            return redirect("contract_detail", contract_id=contract.id)

        messages.error(request, "حدث خطأ أثناء التعديل، راجع البيانات")

    return render(
        request,
        "contracts/contract_form.html",
        {
            "form": form,
            "contract": contract,
            "is_edit": True,
        },
    )


# -----------------------------
# قرار العميل
# -----------------------------
@login_required
def contract_client_decision_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    if request.user.user_type != "client":
        return HttpResponseForbidden("غير مصرح لك")

    if request.method != "POST":
        return redirect("contract_detail", contract_id=contract.id)

    decision = request.POST.get("decision")

    if decision == "approve":
        if hasattr(contract, "status"):
            contract.status = "approved"
            contract.save()
        messages.success(request, "تمت الموافقة على العقد")

    elif decision == "reject":
        if hasattr(contract, "status"):
            contract.status = "rejected"
            contract.save()
        messages.success(request, "تم رفض العقد")

    else:
        messages.error(request, "قرار غير صالح")

    return redirect("contract_detail", contract_id=contract.id)


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
# تحميل PDF
# -----------------------------
@login_required
def contract_download_pdf_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="contract_{contract.contract_number}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)

    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.alignment = TA_RIGHT

    elements = []

    elements.append(Paragraph("عقد صيانة", style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(f"رقم العقد: {contract.contract_number}", style))
    elements.append(Paragraph(f"اسم المبنى: {contract.building_name}", style))
    elements.append(Paragraph(f"الموقع: {contract.building_location}", style))
    elements.append(Paragraph(f"تاريخ البداية: {contract.start_date}", style))
    elements.append(Paragraph(f"تاريخ النهاية: {contract.end_date}", style))

    elements.append(Spacer(1, 20))

    elements.append(Paragraph("بنود العقد:", style))
    elements.append(Spacer(1, 10))

    for clause in contract.clauses.all():
        elements.append(Paragraph(f"- {clause.title}", style))
        elements.append(Paragraph(clause.content, style))
        elements.append(Spacer(1, 10))

    doc.build(elements)

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
