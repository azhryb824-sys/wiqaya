import base64
import os
from io import BytesIO

import arabic_reshaper
import qrcode
from bidi.algorithm import get_display
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from hijridate import Gregorian
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

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


def build_qr_code_buffer(data):
    if not data:
        return None

    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def reshape_arabic_text(text):
    text = str(text or "")
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def register_arabic_font():
    possible_paths = [
        os.path.join(settings.BASE_DIR, "static", "fonts", "Cairo-Regular.ttf"),
        os.path.join(settings.BASE_DIR, "static", "fonts", "DejaVuSans.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("ArabicFont", path))
                return "ArabicFont"
            except Exception:
                continue

    return "Helvetica"


def wrap_text_ar(text, max_chars=70):
    text = str(text or "").strip()
    if not text:
        return []

    words = text.split()
    lines = []
    current = ""

    for word in words:
        test_line = f"{current} {word}".strip()
        if len(test_line) <= max_chars:
            current = test_line
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_rtl_line(pdf, text, x_right, y, font_name="Helvetica", font_size=12):
    pdf.setFont(font_name, font_size)
    pdf.drawRightString(x_right, y, reshape_arabic_text(text))


def draw_wrapped_rtl(pdf, text, x_right, y, font_name="Helvetica", font_size=12, max_chars=70, line_height=18):
    lines = wrap_text_ar(text, max_chars=max_chars)
    for line in lines:
        draw_rtl_line(pdf, line, x_right, y, font_name, font_size)
        y -= line_height
    return y


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
    institution = contract.institution
    clauses = contract.clauses.all().order_by("order", "id")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="contract_{contract.contract_number}.pdf"'

    pdf = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    margin_right = width - 20 * mm
    margin_left = 20 * mm
    y = height - 20 * mm

    font_name = register_arabic_font()

    def new_page():
        pdf.showPage()
        return height - 20 * mm

    pdf.setTitle(f"Contract {contract.contract_number}")
    draw_rtl_line(pdf, "عقد صيانة", margin_right, y, font_name, 18)
    y -= 12 * mm

    contract_number = getattr(contract, "contract_number", "") or "-"
    second_party_name = getattr(contract, "second_party_name", "") or "-"
    building_name = getattr(contract, "building_name", "") or "-"
    building_location = getattr(contract, "building_location", "") or "-"
    created_at_hijri = format_hijri(contract.created_at.date()) if getattr(contract, "created_at", None) else "-"
    start_date_hijri = getattr(contract, "start_date_hijri", "") or format_hijri(getattr(contract, "start_date", None))
    end_date_hijri = getattr(contract, "end_date_hijri", "") or format_hijri(getattr(contract, "end_date", None))
    institution_name = getattr(institution, "name", "") or "المؤسسة"

    info_lines = [
        f"رقم العقد: {contract_number}",
        f"تاريخ الإنشاء: {created_at_hijri}",
        f"تاريخ بداية العقد: {start_date_hijri}",
        f"تاريخ نهاية العقد: {end_date_hijri}",
        f"الطرف الأول: {institution_name}",
        f"الطرف الثاني: {second_party_name}",
        f"اسم المبنى: {building_name}",
        f"موقع المبنى: {building_location}",
    ]

    for line in info_lines:
        draw_rtl_line(pdf, line, margin_right, y, font_name, 12)
        y -= 8 * mm
        if y < 40 * mm:
            y = new_page()

    y -= 4 * mm

    intro_text = (
        f"أنه في يوم {created_at_hijri} تم الاتفاق بين {institution_name} "
        f"و {second_party_name} على أعمال الصيانة الدورية لوسائل السلامة بالمبنى "
        f"\"{building_name}\" الكائن في \"{building_location}\"."
    )
    y = draw_wrapped_rtl(pdf, intro_text, margin_right, y, font_name, 12, max_chars=75, line_height=18)
    y -= 6 * mm

    draw_rtl_line(pdf, "بنود العقد", margin_right, y, font_name, 15)
    y -= 10 * mm

    for idx, clause in enumerate(clauses, start=1):
        title = getattr(clause, "title", "") or f"البند {idx}"
        content = getattr(clause, "content", "") or ""

        block_title = f"{idx}- {title}"
        draw_rtl_line(pdf, block_title, margin_right, y, font_name, 13)
        y -= 7 * mm

        content_lines = wrap_text_ar(content, max_chars=80)
        for line in content_lines:
            draw_rtl_line(pdf, line, margin_right - 5 * mm, y, font_name, 11)
            y -= 6.5 * mm

            if y < 35 * mm:
                y = new_page()

        y -= 4 * mm
        if y < 35 * mm:
            y = new_page()

    google_maps_url = getattr(contract, "google_maps_url", "") or ""
    qr_source = google_maps_url or building_location
    qr_buffer = build_qr_code_buffer(qr_source)

    if y < 65 * mm:
        y = new_page()

    if google_maps_url:
        draw_rtl_line(pdf, f"رابط الموقع: {google_maps_url}", margin_right, y, font_name, 10)
        y -= 10 * mm

    if qr_buffer:
        try:
            qr_image = ImageReader(qr_buffer)
            pdf.drawImage(
                qr_image,
                margin_left,
                y - 30 * mm,
                width=28 * mm,
                height=28 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            pass

    y_sign = 35 * mm

    draw_rtl_line(pdf, "الطرف الأول", width - 50 * mm, y_sign, font_name, 12)
    draw_rtl_line(pdf, "الطرف الثاني", width - 130 * mm, y_sign, font_name, 12)

    draw_rtl_line(pdf, institution_name, width - 50 * mm, y_sign - 8 * mm, font_name, 11)
    draw_rtl_line(pdf, second_party_name, width - 130 * mm, y_sign - 8 * mm, font_name, 11)

    try:
        if getattr(institution, "stamp", None) and institution.stamp.path and os.path.exists(institution.stamp.path):
            pdf.drawImage(
                institution.stamp.path,
                width - 75 * mm,
                10 * mm,
                width=22 * mm,
                height=22 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
    except Exception:
        pass

    try:
        if getattr(institution, "signature", None) and institution.signature.path and os.path.exists(institution.signature.path):
            pdf.drawImage(
                institution.signature.path,
                width - 110 * mm,
                10 * mm,
                width=30 * mm,
                height=15 * mm,
                preserveAspectRatio=True,
                mask="auto",
            )
    except Exception:
        pass

    pdf.save()
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
