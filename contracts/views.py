import base64
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.utils import timezone
from hijridate import Gregorian
from xhtml2pdf import pisa

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


def is_executive(user):
    return user.is_authenticated and user.user_type == "executive"


def is_admin_assistant(user):
    return user.is_authenticated and user.user_type == "admin_assistant"


def is_technician(user):
    return user.is_authenticated and user.user_type == "technician"


def is_client(user):
    return user.is_authenticated and user.user_type == "client"


def can_manage_contracts(user):
    return user.is_authenticated and user.user_type in ["executive", "admin_assistant"]


def get_user_institution(user):
    return user.institutions.first()


def get_contract_for_user_or_404(user, contract_id):
    institution = get_user_institution(user)

    base_qs = MaintenanceContract.objects.select_related(
        "client",
        "institution",
        "executive",
    )

    if is_client(user):
        return get_object_or_404(base_qs, id=contract_id, client=user)

    if is_technician(user):
        return get_object_or_404(
            base_qs.distinct(),
            id=contract_id,
            visits__technician=user,
        )

    if can_manage_contracts(user):
        return get_object_or_404(base_qs, id=contract_id, institution=institution)

    raise HttpResponseForbidden("غير مصرح لك")


def find_client_by_identifier(institution, client_identifier):
    client_identifier = (client_identifier or "").strip()
    if not client_identifier:
        return None, None

    # 1) البحث داخل المؤسسة أولاً
    client = institution.users.filter(
        user_type="client",
        national_id=client_identifier
    ).first()
    if client:
        return client, "national_id"

    client = institution.users.filter(
        user_type="client",
        business_unified_number=client_identifier
    ).first()
    if client:
        return client, "business_unified_number"

    # 2) البحث في كل النظام ثم ربطه بالمؤسسة تلقائياً
    client = User.objects.filter(
        user_type="client",
        national_id=client_identifier
    ).first()
    if client:
        institution.users.add(client)
        return client, "national_id"

    client = User.objects.filter(
        user_type="client",
        business_unified_number=client_identifier
    ).first()
    if client:
        institution.users.add(client)
        return client, "business_unified_number"

    return None, None


def get_second_party_name_for_client(client, identifier_type):
    if not client:
        return ""

    if identifier_type == "business_unified_number" and getattr(client, "business_name", None):
        return client.business_name

    full_name = client.get_full_name().strip()
    return full_name if full_name else client.username


@login_required
def contract_list_view(request):
    institution = get_user_institution(request.user)

    if can_manage_contracts(request.user):
        if not institution:
            messages.error(request, "يجب إنشاء مؤسسة أولاً")
            return redirect("create_institution")

        contracts = MaintenanceContract.objects.filter(
            institution=institution
        ).select_related(
            "client",
            "institution",
            "executive",
        )

    elif is_client(request.user):
        contracts = MaintenanceContract.objects.filter(
            client=request.user
        ).select_related(
            "client",
            "institution",
            "executive",
        )

    elif is_technician(request.user):
        contracts = MaintenanceContract.objects.filter(
            visits__technician=request.user
        ).select_related(
            "client",
            "institution",
            "executive",
        ).distinct()

    else:
        return HttpResponseForbidden("غير مصرح لك")

    return render(
        request,
        "contracts/contract_list.html",
        {
            "contracts": contracts,
            "user_type_label": "العقود",
        },
    )


@login_required
def contract_create_view(request):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden("غير مصرح لك")

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

            client_identifier = (form.cleaned_data.get("client_identifier") or "").strip()
            client, identifier_type = find_client_by_identifier(institution, client_identifier)

            contract.client = client if client else None

            if client:
                contract.second_party_name = get_second_party_name_for_client(client, identifier_type)
            else:
                contract.second_party_name = ""
                if client_identifier:
                    messages.warning(request, "لا يوجد عميل أو منشأة بهذا الرقم")

            if hasattr(contract, "client_status") and not contract.client_status:
                contract.client_status = "pending"

            contract.save()

            selected_templates = form.cleaned_data.get("clause_templates") or []
            for template in selected_templates:
                MaintenanceContractClause.objects.create(
                    contract=contract,
                    title=template.title,
                    content=template.content,
                    order=template.order,
                )

            messages.success(request, "تم إنشاء العقد بنجاح")
            return redirect("contracts_list")

        print(form.errors)
        messages.error(request, "تعذر إنشاء العقد")

    return render(
        request,
        "contracts/contract_form.html",
        {
            "form": form,
            "user_type_label": "العقود",
        },
    )


@login_required
def contract_edit_view(request, contract_id):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden("غير مصرح لك")

    institution = get_user_institution(request.user)

    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    contract = get_object_or_404(
        MaintenanceContract,
        id=contract_id,
        institution=institution
    )

    form = MaintenanceContractForm(
        request.POST or None,
        instance=contract,
        institution=institution
    )

    if request.method == "POST":
        if form.is_valid():
            contract = form.save(commit=False)
            contract.institution = institution
            contract.executive = request.user

            client_identifier = (form.cleaned_data.get("client_identifier") or "").strip()
            client, identifier_type = find_client_by_identifier(institution, client_identifier)

            contract.client = client if client else None

            if client:
                contract.second_party_name = get_second_party_name_for_client(client, identifier_type)
            else:
                contract.second_party_name = ""
                if client_identifier:
                    messages.warning(request, "لا يوجد عميل أو منشأة بهذا الرقم")

            if hasattr(contract, "client_status") and contract.client_status in ["rejected", "revision_requested"]:
                contract.client_status = "pending"
                contract.client_response_note = ""
                contract.client_response_at = None

            contract.save()

            selected_templates = form.cleaned_data.get("clause_templates") or []

            contract.clauses.all().delete()
            for template in selected_templates:
                MaintenanceContractClause.objects.create(
                    contract=contract,
                    title=template.title,
                    content=template.content,
                    order=template.order,
                )

            messages.success(request, "تم تعديل العقد بنجاح")
            return redirect("contract_detail", contract_id=contract.id)

        print(form.errors)
        messages.error(request, "تعذر تعديل العقد، راجع الأخطاء الظاهرة في النموذج")

    else:
        existing_template_titles = contract.clauses.values_list("title", flat=True)
        initial_templates = ContractClauseTemplate.objects.filter(
            institution=institution,
            title__in=existing_template_titles,
            is_active=True,
        )
        form.fields["clause_templates"].initial = initial_templates

    return render(
        request,
        "contracts/contract_form.html",
        {
            "form": form,
            "is_edit": True,
            "contract": contract,
            "user_type_label": "العقود",
        },
    )


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


@login_required
def contract_print_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    qr_source = getattr(contract, "google_maps_url", None) or contract.building_location
    qr_code = build_qr_code_base64(qr_source)

    context = {
        "contract": contract,
        "created_at_hijri": format_hijri(contract.created_at.date()),
        "start_date_hijri": getattr(contract, "start_date_hijri", "") or format_hijri(contract.start_date),
        "end_date_hijri": getattr(contract, "end_date_hijri", "") or format_hijri(contract.end_date),
        "building_location_qr": qr_code,
        "google_maps_url": getattr(contract, "google_maps_url", "") or "",
    }
    return render(request, "contracts/contract_print.html", context)


@login_required
def contract_download_pdf_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    qr_source = getattr(contract, "google_maps_url", None) or contract.building_location
    qr_code = build_qr_code_base64(qr_source)

    context = {
        "contract": contract,
        "created_at_hijri": format_hijri(contract.created_at.date()),
        "start_date_hijri": getattr(contract, "start_date_hijri", "") or format_hijri(contract.start_date),
        "end_date_hijri": getattr(contract, "end_date_hijri", "") or format_hijri(contract.end_date),
        "building_location_qr": qr_code,
        "google_maps_url": getattr(contract, "google_maps_url", "") or "",
        "download_mode": True,
    }

    template = get_template("contracts/contract_print.html")
    html = template.render(context, request)

    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result)

    if pdf.err:
        return HttpResponse("حدث خطأ أثناء إنشاء ملف PDF", status=500)

    filename = f"contract_{contract.contract_number}.pdf"
    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def contract_client_decision_view(request, contract_id):
    if not is_client(request.user):
        return HttpResponseForbidden("غير مصرح لك")

    contract = get_object_or_404(
        MaintenanceContract.objects.select_related(
            "client",
            "institution",
            "executive",
        ),
        id=contract_id,
        client=request.user,
    )

    if request.method != "POST":
        return redirect("contract_detail", contract_id=contract.id)

    decision = request.POST.get("decision")
    note = (request.POST.get("client_response_note") or "").strip()

    if decision not in ["approved", "rejected", "revision_requested"]:
        messages.error(request, "القرار غير صحيح")
        return redirect("contract_detail", contract_id=contract.id)

    if decision in ["rejected", "revision_requested"] and not note:
        messages.error(request, "يرجى كتابة السبب أو التعديل المطلوب")
        return redirect("contract_detail", contract_id=contract.id)

    contract.client_status = decision
    contract.client_response_note = note if note else ""
    contract.client_response_at = timezone.now()
    contract.save(update_fields=["client_status", "client_response_note", "client_response_at"])

    if decision == "approved":
        messages.success(request, "تمت الموافقة على العقد بنجاح")
    elif decision == "rejected":
        messages.success(request, "تم رفض العقد")
    else:
        messages.success(request, "تم إرسال طلب التعديل بنجاح")

    return redirect("contract_detail", contract_id=contract.id)


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
            return redirect("clause_template_list")

        print(form.errors)
        messages.error(request, "تعذر حفظ البند، راجع الأخطاء")

    return render(
        request,
        "contracts/clause_template_form.html",
        {
            "form": form,
            "user_type_label": "العقود",
        },
    )


@login_required
def contract_delete_view(request, contract_id):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden("غير مصرح لك")

    institution = get_user_institution(request.user)

    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    contract = get_object_or_404(
        MaintenanceContract,
        id=contract_id,
        institution=institution
    )

    if request.method == "POST":
        contract.delete()
        messages.success(request, "تم حذف العقد بنجاح")
        return redirect("contracts_list")

    return render(
        request,
        "contracts/contract_confirm_delete.html",
        {
            "contract": contract,
            "user_type_label": "العقود",
        },
    )
