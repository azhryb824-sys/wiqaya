from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from hijridate import Gregorian

from contracts.models import MaintenanceContract
from .forms import CompletionCertificateForm, CertificateClauseTemplateForm
from .models import (
    CertificateClauseTemplate,
    CompletionCertificate,
    CompletionCertificateClause,
)


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


def _get_user_institution(user):
    return user.institutions.first()


def _can_access_certificate(user, certificate):
    if user.user_type in ["executive", "admin_assistant"]:
        institution = _get_user_institution(user)
        return institution and certificate.institution == institution

    if user.user_type == "client":
        return certificate.client == user

    return False


@login_required
def certificate_list_view(request):
    if request.user.user_type == "client":
        certificates = CompletionCertificate.objects.filter(
            client=request.user
        ).select_related("contract", "institution", "executive", "client")
    else:
        institution = _get_user_institution(request.user)
        if not institution:
            messages.error(request, "يجب إنشاء مؤسسة أولاً")
            return redirect("create_institution")

        certificates = CompletionCertificate.objects.filter(
            institution=institution
        ).select_related("contract", "institution", "executive", "client")

    return render(
        request,
        "certificates/certificate_list.html",
        {
            "certificates": certificates,
            "user_type_label": "الشهادات",
        },
    )


@login_required
def certificate_create_view(request, contract_id=None):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = _get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    fixed_contract = None
    if contract_id:
        fixed_contract = get_object_or_404(
            MaintenanceContract,
            id=contract_id,
            institution=institution,
        )

    form = CompletionCertificateForm(
        request.POST or None,
        institution=institution,
        fixed_contract=fixed_contract,
    )

    if request.method == "POST":
        if form.is_valid():
            certificate = form.save(commit=False)

            selected_contract = fixed_contract or form.cleaned_data.get("contract")

            certificate.contract = selected_contract
            certificate.client = selected_contract.client
            certificate.institution = selected_contract.institution
            certificate.executive = request.user

            if not certificate.beneficiary_name:
                certificate.beneficiary_name = selected_contract.second_party_name

            if not certificate.building_name:
                certificate.building_name = selected_contract.building_name

            if not certificate.building_location:
                certificate.building_location = selected_contract.building_location

            if not certificate.expiry_date:
                certificate.expiry_date = selected_contract.end_date

            certificate.save()

            selected_templates = form.cleaned_data.get("clause_templates") or []
            for template in selected_templates:
                selected_work_type = form.cleaned_data.get(f"work_type_{template.id}")

                CompletionCertificateClause.objects.create(
                    certificate=certificate,
                    clause_type=template.clause_type,
                    work_type=selected_work_type,
                    title=template.title,
                    details=template.details,
                    contract_expiry_date=selected_contract.end_date,
                    order=template.order,
                )

            messages.success(request, "تم إنشاء الشهادة بنجاح")
            return redirect("certificate_detail", certificate_id=certificate.id)

        messages.error(request, "تعذر إنشاء الشهادة، راجع الأخطاء الظاهرة في النموذج")

    clause_rows = []
    for template in form.fields["clause_templates"].queryset:
        clause_rows.append({
            "template": template,
            "checkbox_name": "clause_templates",
            "checkbox_value": str(template.id),
            "checkbox_checked": str(template.id) in request.POST.getlist("clause_templates"),
            "work_field": form[f"work_type_{template.id}"],
        })

    return render(
        request,
        "certificates/certificate_form.html",
        {
            "form": form,
            "user_type_label": "الشهادات",
            "fixed_contract": fixed_contract,
            "clause_rows": clause_rows,
        },
    )

@login_required
def certificate_detail_view(request, certificate_id):
    certificate = get_object_or_404(
        CompletionCertificate.objects.select_related(
            "contract",
            "institution",
            "executive",
            "client",
        ),
        id=certificate_id,
    )

    if not _can_access_certificate(request.user, certificate):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    return render(
        request,
        "certificates/certificate_detail.html",
        {
            "certificate": certificate,
            "user_type_label": "الشهادات",
        },
    )


@login_required
def certificate_print_view(request, certificate_id):
    certificate = get_object_or_404(
        CompletionCertificate.objects.select_related(
            "contract",
            "institution",
            "executive",
            "client",
        ),
        id=certificate_id,
    )

    if not _can_access_certificate(request.user, certificate):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    context = {
        "certificate": certificate,
        "issue_date_hijri": format_hijri(certificate.issue_date),
        "expiry_date_hijri": format_hijri(certificate.expiry_date) if certificate.expiry_date else "-",
    }
    return render(request, "certificates/certificate_print.html", context)


@login_required
def certificate_clause_template_list_view(request):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = _get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    templates = CertificateClauseTemplate.objects.filter(
        institution=institution
    ).order_by("clause_type", "order", "id")

    return render(
        request,
        "certificates/certificate_clause_list.html",
        {
            "templates": templates,
            "user_type_label": "الشهادات",
        },
    )


@login_required
def certificate_clause_template_create_view(request):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = _get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    form = CertificateClauseTemplateForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            clause = form.save(commit=False)
            clause.institution = institution
            clause.save()
            messages.success(request, "تم إضافة بند الشهادة بنجاح")
            return redirect("certificate_clause_list")

        messages.error(request, "تعذر حفظ بند الشهادة، راجع البيانات")

    return render(
        request,
        "certificates/certificate_clause_form.html",
        {
            "form": form,
            "user_type_label": "الشهادات",
        },
    )
