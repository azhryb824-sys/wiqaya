import base64
from io import BytesIO

import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from contracts.models import MaintenanceContract
from .forms import VisitForm, VisitNoteForm
from .models import Visit
from django.http import HttpResponse
from django.template.loader import render_to_string



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


def send_html_email(subject, to_emails, html_template, text_template=None, context=None):
    context = context or {}

    if not to_emails:
        return

    html_body = render_to_string(html_template, context)

    if text_template:
        text_body = render_to_string(text_template, context)
    else:
        text_body = "هذه رسالة آلية من منصة وقاية."

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_emails,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send()


def send_technician_notification(request, technician, visit):
    if not technician or not technician.email:
        return

    action_url = request.build_absolute_uri(
        reverse("visit_detail", args=[visit.id])
    )

    context = {
        "technician_name": technician.get_display_name(),
        "visit_date": visit.visit_date,
        "contract_number": visit.contract.contract_number,
        "building_name": visit.contract.building_name,
        "action_url": action_url,
    }

    send_html_email(
        subject="تم تعيين زيارة جديدة لك | منصة وقاية",
        to_emails=[technician.email],
        html_template="emails/technician_visit.html",
        text_template="emails/technician_visit.txt",
        context=context,
    )


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
                return render(request, "visits/visit_form.html", {"form": form})

            duplicate_visit = Visit.objects.filter(
                contract=contract,
                visit_date__year=visit.visit_date.year,
                visit_date__month=visit.visit_date.month,
            ).exists()

            if duplicate_visit:
                messages.error(request, "توجد زيارة في نفس الشهر")
                return render(request, "visits/visit_form.html", {"form": form})

            visit.save()

            if visit.technician:
                try:
                    send_technician_notification(request, visit.technician, visit)
                except Exception as exc:
                    print("Technician email error:", exc)
                    messages.warning(request, "تم إنشاء الزيارة لكن تعذر إرسال إشعار الفني")

            messages.success(request, "تم إنشاء الزيارة")
            return redirect("visit_list")

    return render(request, "visits/visit_form.html", {"form": form})


@login_required
def visit_detail_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if not _can_access_visit(request.user, visit):
        messages.error(request, "غير مصرح")
        return redirect("visit_list")

    return render(request, "visits/visit_detail.html", {"visit": visit})


@login_required
def visit_print_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if not _can_access_visit(request.user, visit):
        return redirect("visit_list")

    return render(request, "visits/visit_print.html", {"visit": visit})


@login_required
def visit_add_note_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "technician":
        return redirect("visit_list")

    form = VisitNoteForm(request.POST or None, instance=visit)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("visit_detail", visit_id=visit.id)

    return render(request, "visits/monthly_note_form.html", {"form": form})


@login_required
def visit_technician_approve_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "technician":
        return redirect("visit_list")

    visit.technician_approved = True
    visit.technician_approved_at = timezone.now()
    visit.save()

    return redirect("visit_detail", visit_id=visit.id)


@login_required
def visit_client_approve_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "client":
        return redirect("visit_list")

    visit.client_approved = True
    visit.client_approved_at = timezone.now()
    visit.save()

    return redirect("visit_detail", visit_id=visit.id)


@login_required
def contract_visits_log_view(request, contract_id):
    contract = get_object_or_404(MaintenanceContract, id=contract_id)
    visits = contract.visits.all()

    return render(
        request,
        "visits/contract_visits_log.html",
        {"contract": contract, "visits": visits},
    )


@login_required
def contract_visits_log_print_view(request, contract_id):
    contract = get_object_or_404(MaintenanceContract, id=contract_id)
    visits = contract.visits.all()

    return render(
        request,
        "visits/contract_visits_log_print.html",
        {"contract": contract, "visits": visits},
    )


@login_required
def visit_sign_technician_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.method == "POST":
        visit.technician_signature = request.POST.get("signature_data")
        visit.save()
        return redirect("visit_detail", visit_id=visit.id)

    return render(request, "visits/sign_visit.html", {"visit": visit})


# =========================
# 🔥 التعديل
# =========================
@login_required
def visit_edit_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "executive":
        return redirect("visit_list")

    if visit.technician_approved or visit.client_approved:
        messages.error(request, "لا يمكن تعديل الزيارة بعد اعتمادها")
        return redirect("visit_detail", visit_id=visit.id)

    old_technician_id = visit.technician_id

    form = VisitForm(request.POST or None, instance=visit)

    if request.method == "POST" and form.is_valid():
        visit = form.save()

        if visit.technician and visit.technician_id != old_technician_id:
            try:
                send_technician_notification(request, visit.technician, visit)
            except Exception as exc:
                print("Technician email error:", exc)
                messages.warning(request, "تم تعديل الزيارة لكن تعذر إرسال إشعار الفني")

        messages.success(request, "تم التعديل")
        return redirect("visit_detail", visit_id=visit.id)

    return render(request, "visits/visit_form.html", {"form": form, "is_edit": True})


# =========================
# 🔥 الحذف
# =========================
@login_required
def visit_delete_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    if request.user.user_type != "executive":
        return redirect("visit_list")

    if visit.technician_approved or visit.client_approved:
        messages.error(request, "لا يمكن حذف الزيارة بعد اعتمادها")
        return redirect("visit_detail", visit_id=visit.id)

    if request.method == "POST":
        contract_id = visit.contract.id
        visit.delete()
        messages.success(request, "تم الحذف")
        return redirect("contract_visits_log", contract_id=contract_id)

    return render(request, "visits/visit_confirm_delete.html", {"visit": visit})
@login_required
def visits_log_download_pdf_view(request, contract_id):
    contract = get_object_or_404(
        MaintenanceContract.objects.select_related("institution", "client", "executive"),
        id=contract_id,
    )
    visits = contract.visits.all().select_related("technician")

    html_string = render_to_string(
        "visits/visits_log_print.html",
        {
            "contract": contract,
            "visits": visits,
        },
        request=request,
    )

    pdf_file = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf()

    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="visits_log_{contract.contract_number}.pdf"'
    return response
