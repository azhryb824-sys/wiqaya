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
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from hijridate import Gregorian

from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

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
# صلاحيات ومساعدات أمنية
# -----------------------------
def is_client(user):
    return user.is_authenticated and user.user_type == "client"



def can_manage_contracts(user):
    return user.is_authenticated and user.user_type in ["executive", "admin_assistant"]



def get_user_institution(user):
    return user.institutions.first()



def is_contract_deleted(contract):
    return bool(getattr(contract, "is_deleted", False))



def can_edit_contract(contract):
    status = getattr(contract, "status", None)
    if not status:
        return True
    return status in ["draft", "revision_requested", "pending"]



def log_action(request, action, contract, note=""):
    # مؤقتاً كسجل بسيط في اللوق إلى حين إضافة AuditLog Model
    print(
        "[AUDIT]",
        f"user_id={getattr(request.user, 'id', None)}",
        f"username={getattr(request.user, 'username', '')}",
        f"action={action}",
        f"contract_id={getattr(contract, 'id', None)}",
        f"note={note}",
    )



def ensure_contract_not_deleted(contract):
    if is_contract_deleted(contract):
        raise Http404("هذا العقد غير متاح")



def get_contract_for_user_or_404(user, contract_id):
    institution = get_user_institution(user)

    qs = MaintenanceContract.objects.select_related(
        "client",
        "institution",
        "executive",
    )

    if is_client(user):
        contract = get_object_or_404(qs, id=contract_id, client=user)
        ensure_contract_not_deleted(contract)
        return contract

    if can_manage_contracts(user):
        if not institution:
            raise Http404("لا توجد مؤسسة مرتبطة بهذا المستخدم")
        contract = get_object_or_404(qs, id=contract_id, institution=institution)
        ensure_contract_not_deleted(contract)
        return contract

    raise Http404("غير مصرح لك")


# -----------------------------
# دوال مساعدة لربط العميل
# -----------------------------
def get_institution_clients(institution):
    if not institution:
        return User.objects.none()

    if hasattr(institution, "users"):
        return institution.users.filter(user_type="client")

    return User.objects.filter(user_type="client")



def get_client_full_name(client):
    full_name = f"{getattr(client, 'first_name', '')} {getattr(client, 'last_name', '')}".strip()
    return full_name or getattr(client, "username", "") or ""



def get_client_second_party_name(client):
    business_name = (
        getattr(client, "business_name", None)
        or getattr(client, "company_name", None)
        or getattr(client, "establishment_name", None)
        or getattr(client, "client_business_name", None)
    )
    return business_name or get_client_full_name(client)



def find_client_by_identifier(institution, identifier):
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    clients = get_institution_clients(institution)

    query = (
        Q(national_id=identifier)
        | Q(phone=identifier)
        | Q(email=identifier)
        | Q(username=identifier)
    )

    optional_fields = [
        "business_unified_number",
        "unified_number",
        "commercial_registration",
    ]

    model_field_names = {field.name for field in User._meta.get_fields() if hasattr(field, "name")}
    for field_name in optional_fields:
        if field_name in model_field_names:
            query |= Q(**{field_name: identifier})

    return clients.filter(query).first()



def apply_client_linking_to_contract(contract, cleaned_data, institution):
    selected_client = cleaned_data.get("client")
    client_identifier = (cleaned_data.get("client_identifier") or "").strip()
    second_party_name = (cleaned_data.get("second_party_name") or "").strip()

    client = selected_client

    if not client and client_identifier:
        client = find_client_by_identifier(institution, client_identifier)

    if client:
        contract.client = client

        if not client_identifier:
            contract.client_identifier = getattr(client, "national_id", "") or ""
        else:
            contract.client_identifier = client_identifier

        if not second_party_name:
            contract.second_party_name = get_client_second_party_name(client)
        else:
            contract.second_party_name = second_party_name
    else:
        contract.client = None
        contract.client_identifier = client_identifier
        if second_party_name:
            contract.second_party_name = second_party_name

    return client


# -----------------------------
# عرض العقود
# -----------------------------
@login_required
def contract_list_view(request):
    institution = get_user_institution(request.user)

    if can_manage_contracts(request.user):
        if not institution:
            messages.error(request, "يجب إنشاء مؤسسة أولاً")
            return redirect("create_institution")

        contracts = MaintenanceContract.objects.filter(
            institution=institution
        ).select_related("client", "institution", "executive")
    elif is_client(request.user):
        contracts = MaintenanceContract.objects.filter(
            client=request.user
        ).select_related("client", "institution", "executive")
    else:
        return HttpResponseForbidden()

    if hasattr(MaintenanceContract, "is_deleted"):
        contracts = contracts.filter(is_deleted=False)

    return render(
        request,
        "contracts/contract_list.html",
        {
            "contracts": contracts,
            "user_type_label": "العقود",
        },
    )


# -----------------------------
# إنشاء عقد
# -----------------------------
@login_required
def contract_create_view(request):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden()

    institution = get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    form = MaintenanceContractForm(request.POST or None, institution=institution)

    if request.method == "POST":
        if form.is_valid():
            contract = form.save(commit=False)
            contract.institution = institution
            contract.executive = request.user

            linked_client = apply_client_linking_to_contract(
                contract=contract,
                cleaned_data=form.cleaned_data,
                institution=institution,
            )

            if not linked_client and (form.cleaned_data.get("client_identifier") or "").strip():
                form.add_error("client_identifier", "لم يتم العثور على عميل مطابق لهذا المعرّف داخل المؤسسة.")
                messages.error(request, "تعذر إنشاء العقد، راجع البيانات")
            else:
                contract.save()

                selected_templates = form.cleaned_data.get("clause_templates") or []
                for template in selected_templates:
                    MaintenanceContractClause.objects.create(
                        contract=contract,
                        title=template.title,
                        content=template.content,
                        order=template.order,
                    )

                log_action(request, "create_contract", contract)
                messages.success(request, "تم إنشاء العقد")
                return redirect("contracts:contracts_list")

        else:
            messages.error(request, "تعذر إنشاء العقد، راجع البيانات")

    return render(
        request,
        "contracts/contract_form.html",
        {
            "form": form,
            "user_type_label": "العقود",
        },
    )


# -----------------------------
# تفاصيل
# -----------------------------
@login_required
def contract_detail_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)
    return render(
        request,
        "contracts/contract_detail.html",
        {
            "contract": contract,
            "user_type_label": "العقود",
        },
    )


# -----------------------------
# تعديل عقد
# -----------------------------
@login_required
def contract_edit_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    if request.user.user_type not in ["executive", "admin_assistant"]:
        return HttpResponseForbidden("غير مصرح لك")

    if not can_edit_contract(contract):
        messages.error(request, "لا يمكن تعديل هذا العقد بعد اعتماده أو إغلاقه")
        return redirect("contracts:contract_detail", contract_id=contract.id)

    institution = get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

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

            linked_client = apply_client_linking_to_contract(
                contract=updated_contract,
                cleaned_data=form.cleaned_data,
                institution=institution,
            )

            if not linked_client and (form.cleaned_data.get("client_identifier") or "").strip():
                form.add_error("client_identifier", "لم يتم العثور على عميل مطابق لهذا المعرّف داخل المؤسسة.")
                messages.error(request, "حدث خطأ أثناء التعديل، راجع البيانات")
            else:
                updated_contract.save()

                selected_templates = form.cleaned_data.get("clause_templates") or []
                contract.clauses.all().delete()
                for template in selected_templates:
                    MaintenanceContractClause.objects.create(
                        contract=updated_contract,
                        title=template.title,
                        content=template.content,
                        order=template.order,
                    )

                log_action(request, "update_contract", updated_contract)
                messages.success(request, "تم تعديل العقد بنجاح")
                return redirect("contracts:contract_detail", contract_id=contract.id)

        else:
            messages.error(request, "حدث خطأ أثناء التعديل، راجع البيانات")

    return render(
        request,
        "contracts/contract_form.html",
        {
            "form": form,
            "contract": contract,
            "is_edit": True,
            "user_type_label": "العقود",
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
        return redirect("contracts:contract_detail", contract_id=contract.id)

    current_status = getattr(contract, "status", None)
    if current_status in ["approved", "cancelled", "expired"]:
        messages.error(request, "لا يمكن اتخاذ قرار جديد على هذا العقد")
        return redirect("contracts:contract_detail", contract_id=contract.id)

    decision = request.POST.get("decision")

    if decision == "approve":
        if hasattr(contract, "status"):
            contract.status = "approved"
            contract.save(update_fields=["status"])
        log_action(request, "client_approve_contract", contract)
        messages.success(request, "تمت الموافقة على العقد")

    elif decision == "reject":
        if hasattr(contract, "status"):
            contract.status = "rejected"
            contract.save(update_fields=["status"])
        log_action(request, "client_reject_contract", contract)
        messages.success(request, "تم رفض العقد")

    elif decision == "revision_requested":
        if hasattr(contract, "status"):
            contract.status = "revision_requested"
            contract.save(update_fields=["status"])
        log_action(request, "client_request_revision_contract", contract)
        messages.success(request, "تم إرسال طلب التعديل")

    else:
        messages.error(request, "قرار غير صالح")

    return redirect("contracts:contract_detail", contract_id=contract.id)


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

    log_action(request, "download_contract_pdf", contract)
    doc.build(elements)
    return response


# -----------------------------
# حذف
# -----------------------------
@login_required
def contract_delete_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    if request.user.user_type != "executive":
        return HttpResponseForbidden("فقط المدير التنفيذي يمكنه حذف العقد")

    if getattr(contract, "status", None) == "approved":
        messages.error(request, "لا يمكن حذف عقد تمت الموافقة عليه")
        return redirect("contracts:contract_detail", contract_id=contract.id)

    if request.method == "POST":
        if hasattr(contract, "is_deleted"):
            contract.is_deleted = True
            if hasattr(contract, "deleted_at"):
                contract.deleted_at = timezone.now()
            if hasattr(contract, "deleted_by"):
                contract.deleted_by = request.user

            update_fields = ["is_deleted"]
            if hasattr(contract, "deleted_at"):
                update_fields.append("deleted_at")
            if hasattr(contract, "deleted_by"):
                update_fields.append("deleted_by")

            contract.save(update_fields=update_fields)
        else:
            contract.delete()

        log_action(request, "delete_contract", contract)
        messages.success(request, "تم حذف العقد")
        return redirect("contracts:contracts_list")

    return render(
        request,
        "contracts/contract_confirm_delete.html",
        {
            "contract": contract,
            "user_type_label": "العقود",
        },
    )


# -----------------------------
# قائمة قوالب البنود
# -----------------------------
@login_required
def clause_template_list_view(request):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden("غير مصرح لك")

    institution = get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    templates = ContractClauseTemplate.objects.filter(
        institution=institution
    ).order_by("order", "id")

    return render(
        request,
        "contracts/clause_template_list.html",
        {
            "templates": templates,
            "user_type_label": "العقود",
        },
    )


# -----------------------------
# إنشاء قالب بند
# -----------------------------
@login_required
def clause_template_create_view(request):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden("غير مصرح لك")

    institution = get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    form = ContractClauseTemplateForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            clause_template = form.save(commit=False)
            clause_template.institution = institution
            clause_template.save()

            messages.success(request, "تم إضافة قالب البند بنجاح")
            return redirect("contracts:clause_template_list")

        messages.error(request, "تعذر حفظ البند، راجع الأخطاء")

    return render(
        request,
        "contracts/clause_template_form.html",
        {
            "form": form,
            "user_type_label": "العقود",
        },
    )
