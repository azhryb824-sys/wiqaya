import base64
from io import BytesIO

import qrcode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from contracts.models import MaintenanceContract
from .forms import VisitForm, VisitNoteForm
from .models import Visit


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


def _get_user_institution(user):
    return user.institutions.first()


def _can_access_contract(user, contract):
    if user.user_type in ["executive", "admin_assistant"]:
        institution = _get_user_institution(user)
        return institution and contract.institution == institution

    if user.user_type == "technician":
        return contract.visits.filter(technician=user).exists()

    if user.user_type == "client":
        return contract.client == user

    return False


def _can_access_visit(user, visit):
    if user.user_type in ["executive", "admin_assistant"]:
        institution = _get_user_institution(user)
        return institution and visit.contract.institution == institution

    if user.user_type == "technician":
        return visit.technician == user

    if user.user_type == "client":
        return visit.contract.client == user

    return False


@login_required
def visit_list_view(request):
    if request.user.user_type == "technician":
        visits = Visit.objects.filter(technician=request.user).select_related(
            "contract", "contract__institution", "technician"
        )
    elif request.user.user_type == "client":
        visits = Visit.objects.filter(contract__client=request.user).select_related(
            "contract", "contract__institution", "technician"
        )
    else:
        institution = _get_user_institution(request.user)
        if not institution:
            messages.error(request, "يجب إنشاء مؤسسة أولاً")
            return redirect("create_institution")

        visits = Visit.objects.filter(contract__institution=institution).select_related(
            "contract", "contract__institution", "technician"
        )

    return render(
        request,
        "visits/visit_list.html",
        {
            "visits": visits,
            "user_type_label": "الزيارات",
        },
    )


@login_required
def visit_create_view(request):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = _get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    form = VisitForm(request.POST or None, institution=institution)

    if request.method == "POST":
        if form.is_valid():
            visit = form.save(commit=False)
            contract = visit.contract

            if contract.institution != institution:
                messages.error(request, "العقد المحدد غير تابع لمؤسستك")
                return redirect("visit_list")

            if contract.end_date < visit.visit_date:
                messages.error(request, "لا يمكن إنشاء زيارة بعد انتهاء العقد")
                return render(
                    request,
                    "visits/visit_form.html",
                    {
                        "form": form,
                        "user_type_label": "الزيارات",
                    },
                )

            duplicate_visit = Visit.objects.filter(
                contract=contract,
                visit_date__year=visit.visit_date.year,
                visit_date__month=visit.visit_date.month,
            ).exists()

            if duplicate_visit:
                messages.error(request, "توجد زيارة مسجلة لهذا العقد في نفس الشهر بالفعل")
                return render(
                    request,
                    "visits/visit_form.html",
                    {
                        "form": form,
                        "user_type_label": "الزيارات",
                    },
                )

            visit.save()
            messages.success(request, "تم إنشاء الزيارة بنجاح")
            return redirect("visit_list")

        print(form.errors)
        messages.error(request, "تعذر إنشاء الزيارة، راجع الأخطاء الظاهرة في النموذج")

    return render(
        request,
        "visits/visit_form.html",
        {
            "form": form,
            "user_type_label": "الزيارات",
        },
    )


@login_required
def visit_detail_view(request, visit_id):
    visit = get_object_or_404(
        Visit.objects.select_related(
            "contract",
            "contract__institution",
            "contract__client",
            "technician",
        ),
        id=visit_id,
    )

    if not _can_access_visit(request.user, visit):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("visit_list")

    return render(
        request,
        "visits/visit_detail.html",
        {
            "visit": visit,
            "user_type_label": "الزيارات",
        },
    )


@login_required
def visit_print_view(request, visit_id):
    visit = get_object_or_404(
        Visit.objects.select_related(
            "contract",
            "contract__institution",
            "technician",
            "contract__client",
        ),
        id=visit_id,
    )

    if not _can_access_visit(request.user, visit):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("visit_list")

    qr_code = build_qr_code_base64(visit.contract.building_location)

    return render(
        request,
        "visits/visit_print.html",
        {
            "visit": visit,
            "building_location_qr": qr_code,
        },
    )


@login_required
def visit_add_note_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "technician" or visit.technician != request.user:
        messages.error(request, "غير مصرح لك بإضافة ملاحظات لهذه الزيارة")
        return redirect("visit_list")

    form = VisitNoteForm(request.POST or None, instance=visit)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "تم حفظ الملاحظات بنجاح")
            return redirect("visit_detail", visit_id=visit.id)

        print(form.errors)
        messages.error(request, "تعذر حفظ الملاحظات، راجع الأخطاء الظاهرة")

    return render(
        request,
        "visits/monthly_note_form.html",
        {
            "form": form,
            "visit": visit,
            "user_type_label": "الزيارات",
        },
    )


@login_required
def visit_technician_approve_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "technician" or visit.technician != request.user:
        messages.error(request, "غير مصرح لك باعتماد هذه الزيارة")
        return redirect("visit_list")

    if not visit.notes or not str(visit.notes).strip():
        messages.error(request, "يجب إدخال ملاحظات الفني قبل اعتماد الزيارة")
        return redirect("visit_add_note", visit_id=visit.id)

    if visit.technician_approved:
        messages.info(request, "تم اعتماد الزيارة مسبقاً من الفني")
        return redirect("visit_detail", visit_id=visit.id)

    visit.technician_approved = True
    visit.technician_approved_at = timezone.now()
    visit.save(update_fields=["technician_approved", "technician_approved_at"])

    messages.success(request, "تم اعتماد الزيارة من الفني")
    return redirect("visit_detail", visit_id=visit.id)


@login_required
def visit_client_approve_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "client" or visit.contract.client != request.user:
        messages.error(request, "غير مصرح لك باعتماد هذه الزيارة")
        return redirect("visit_list")

    if not visit.technician_approved:
        messages.error(request, "لا يمكن اعتماد الزيارة قبل اعتماد الفني")
        return redirect("visit_detail", visit_id=visit.id)

    if visit.client_approved:
        messages.info(request, "تم اعتماد الزيارة مسبقاً من العميل")
        return redirect("visit_detail", visit_id=visit.id)

    visit.client_approved = True
    visit.client_approved_at = timezone.now()
    visit.save(update_fields=["client_approved", "client_approved_at"])

    messages.success(request, "تم اعتماد الزيارة من العميل")
    return redirect("visit_detail", visit_id=visit.id)


@login_required
def contract_visits_log_view(request, contract_id):
    contract = get_object_or_404(
        MaintenanceContract.objects.select_related("institution", "client"),
        id=contract_id,
    )

    if not _can_access_contract(request.user, contract):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    visits = contract.visits.select_related("technician").all()
    qr_code = build_qr_code_base64(contract.building_location)

    return render(
        request,
        "visits/contract_visits_log.html",
        {
            "contract": contract,
            "visits": visits,
            "user_type_label": "الزيارات",
            "building_location_qr": qr_code,
        },
    )


@login_required
def contract_visits_log_print_view(request, contract_id):
    contract = get_object_or_404(
        MaintenanceContract.objects.select_related("institution", "client"),
        id=contract_id,
    )

    if not _can_access_contract(request.user, contract):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    visits = contract.visits.select_related("technician").all()
    qr_code = build_qr_code_base64(contract.building_location)

    return render(
        request,
        "visits/contract_visits_log_print.html",
        {
            "contract": contract,
            "visits": visits,
            "building_location_qr": qr_code,
        },
    )
@login_required
def visit_sign_technician_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "technician" or visit.technician != request.user:
        messages.error(request, "غير مصرح لك بتوقيع هذه الزيارة")
        return redirect("visit_list")

    if request.method == "POST":
        signature_data = request.POST.get("signature_data", "").strip()

        if not signature_data:
            messages.error(request, "يرجى إضافة التوقيع أولاً")
            return redirect("visit_sign_technician", visit_id=visit.id)

        visit.technician_signature = signature_data
        visit.save(update_fields=["technician_signature"])

        messages.success(request, "تم حفظ توقيع الفني بنجاح")
        return redirect("visit_detail", visit_id=visit.id)

    return render(
        request,
        "visits/sign_visit.html",
        {
            "visit": visit,
            "page_title": "توقيع الفني الإلكتروني",
            "user_type_label": "الزيارات",
        },
    )