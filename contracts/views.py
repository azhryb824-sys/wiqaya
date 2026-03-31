import base64
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from hijridate import Gregorian

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
        return get_object_or_404(base_qs.distinct(), id=contract_id, visits__technician=user)

    if can_manage_contracts(user):
        return get_object_or_404(base_qs, id=contract_id, institution=institution)

    raise HttpResponseForbidden("غير مصرح لك")


# ================================
# إنشاء عقد (🔥 تم التعديل هنا)
# ================================
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

            client = form.cleaned_data.get("client")
            client_identifier = (form.cleaned_data.get("client_identifier") or "").strip()

            identifier_type = None

            if not client and client_identifier:
                # 🔍 البحث برقم الهوية
                client = institution.users.filter(
                    user_type="client",
                    national_id=client_identifier
                ).first()

                if client:
                    identifier_type = "national_id"

                # 🔍 البحث بالرقم الموحد
                if not client:
                    client = institution.users.filter(
                        user_type="client",
                        business_unified_number=client_identifier
                    ).first()

                    if client:
                        identifier_type = "business_unified_number"

            contract.client = client if client else None

            # 🔥 تعبئة الطرف الثاني تلقائيًا
            if client:
                if identifier_type == "business_unified_number" and client.business_name:
                    contract.second_party_name = client.business_name
                else:
                    full_name = client.get_full_name().strip()
                    contract.second_party_name = full_name if full_name else client.username

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

    return render(request, "contracts/contract_form.html", {"form": form})


# ================================
# تعديل عقد (🔥 تم التعديل هنا)
# ================================
@login_required
def contract_edit_view(request, contract_id):
    if not can_manage_contracts(request.user):
        return HttpResponseForbidden("غير مصرح لك")

    institution = get_user_institution(request.user)

    contract = get_object_or_404(MaintenanceContract, id=contract_id, institution=institution)

    form = MaintenanceContractForm(request.POST or None, instance=contract, institution=institution)

    if request.method == "POST":
        if form.is_valid():
            contract = form.save(commit=False)
            contract.executive = request.user

            client = form.cleaned_data.get("client")
            client_identifier = (form.cleaned_data.get("client_identifier") or "").strip()

            identifier_type = None

            if not client and client_identifier:
                client = institution.users.filter(
                    user_type="client",
                    national_id=client_identifier
                ).first()

                if client:
                    identifier_type = "national_id"

                if not client:
                    client = institution.users.filter(
                        user_type="client",
                        business_unified_number=client_identifier
                    ).first()

                    if client:
                        identifier_type = "business_unified_number"

            contract.client = client if client else None

            if client:
                if identifier_type == "business_unified_number" and client.business_name:
                    contract.second_party_name = client.business_name
                else:
                    full_name = client.get_full_name().strip()
                    contract.second_party_name = full_name if full_name else client.username

            contract.save()

            messages.success(request, "تم تعديل العقد بنجاح")
            return redirect("contract_detail", contract_id=contract.id)

    return render(request, "contracts/contract_form.html", {"form": form, "is_edit": True})
