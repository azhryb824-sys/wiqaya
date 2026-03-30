import base64
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
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

    qr = qrcode.QRCode(
        version=1,
        box_size=6,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{encoded}"


@login_required
def contract_list_view(request):
    institution = request.user.institutions.first()

    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    contracts = MaintenanceContract.objects.filter(institution=institution).select_related(
        "client",
        "institution",
        "executive",
    )
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
    institution = request.user.institutions.first()

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
            client_identifier = form.cleaned_data.get("client_identifier")

            if not client and client_identifier:
                client = institution.users.filter(
                    user_type="client",
                    national_id=client_identifier
                ).first()

            if client:
                contract.client = client

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
        messages.error(request, "تعذر إنشاء العقد، راجع الأخطاء الظاهرة في النموذج")

    return render(
        request,
        "contracts/contract_form.html",
        {
            "form": form,
            "user_type_label": "العقود",
        },
    )


@login_required
def contract_detail_view(request, contract_id):
    institution = request.user.institutions.first()

    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    contract = get_object_or_404(
        MaintenanceContract.objects.select_related(
            "client",
            "institution",
            "executive",
        ),
        id=contract_id,
        institution=institution,
    )
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
    institution = request.user.institutions.first()

    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    contract = get_object_or_404(
        MaintenanceContract.objects.select_related(
            "client",
            "institution",
            "executive",
        ),
        id=contract_id,
        institution=institution
    )

    qr_code = build_qr_code_base64(contract.building_location)

    context = {
        "contract": contract,
        "created_at_hijri": format_hijri(contract.created_at.date()),
        "start_date_hijri": contract.start_date_hijri or format_hijri(contract.start_date),
        "end_date_hijri": contract.end_date_hijri or format_hijri(contract.end_date),
        "building_location_qr": qr_code,
    }
    return render(request, "contracts/contract_print.html", context)


@login_required
def clause_template_list_view(request):
    institution = request.user.institutions.first()

    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    templates = ContractClauseTemplate.objects.filter(institution=institution).order_by("order", "id")
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
    institution = request.user.institutions.first()

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
def contract_edit_view(request, contract_id):
    institution = request.user.institutions.first()

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

            client = form.cleaned_data.get("client")
            client_identifier = form.cleaned_data.get("client_identifier")

            if not client and client_identifier:
                client = institution.users.filter(
                    user_type="client",
                    national_id=client_identifier
                ).first()

            contract.client = client if client else None
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
        existing_template_ids = contract.clauses.values_list("title", flat=True)
        initial_templates = ContractClauseTemplate.objects.filter(
            institution=institution,
            title__in=existing_template_ids,
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
def contract_delete_view(request, contract_id):
    institution = request.user.institutions.first()

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
