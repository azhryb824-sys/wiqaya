from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    PriceQuotationForm,
    PriceQuotationItemFormSet,
    PriceQuotationInstallmentFormSet,
)
from .models import PriceQuotation


def _get_user_institution(user):
    return user.institutions.first()


def _can_access_quotation(user, quotation):
    if user.user_type in ["executive", "admin_assistant"]:
        institution = _get_user_institution(user)
        return institution and quotation.institution == institution

    if user.user_type == "client":
        return quotation.client == user

    return False


def _render_quotation_form(
    request,
    *,
    form,
    item_formset,
    installment_formset,
    page_title,
):
    return render(
        request,
        "quotations/quotation_form.html",
        {
            "form": form,
            "item_formset": item_formset,
            "installment_formset": installment_formset,
            "item_empty_form": item_formset.empty_form,
            "installment_empty_form": installment_formset.empty_form,
            "page_title": page_title,
            "user_type_label": "عروض الأسعار",
        },
    )


@login_required
def quotation_list_view(request):
    if request.user.user_type == "client":
        quotations = PriceQuotation.objects.filter(
            client=request.user
        ).select_related(
            "institution",
            "executive",
            "client",
        ).prefetch_related(
            "items",
            "installments",
        ).order_by("-id")

    elif request.user.user_type in ["executive", "admin_assistant"]:
        institution = _get_user_institution(request.user)
        if not institution:
            messages.error(request, "يجب إنشاء مؤسسة أولاً")
            return redirect("create_institution")

        quotations = PriceQuotation.objects.filter(
            institution=institution
        ).select_related(
            "institution",
            "executive",
            "client",
        ).prefetch_related(
            "items",
            "installments",
        ).order_by("-id")

    else:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    return render(
        request,
        "quotations/quotation_list.html",
        {
            "quotations": quotations,
            "user_type_label": "عروض الأسعار",
        },
    )


@login_required
def quotation_create_view(request):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = _get_user_institution(request.user)
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً")
        return redirect("create_institution")

    if request.method == "POST":
        form = PriceQuotationForm(
            request.POST,
            institution=institution,
        )
        item_formset = PriceQuotationItemFormSet(request.POST, prefix="items")
        installment_formset = PriceQuotationInstallmentFormSet(request.POST, prefix="installments")

        if form.is_valid() and item_formset.is_valid() and installment_formset.is_valid():
            valid_items = []
            for item_form in item_formset:
                if not hasattr(item_form, "cleaned_data") or not item_form.cleaned_data:
                    continue
                if item_form.cleaned_data.get("DELETE", False):
                    continue
                valid_items.append(item_form)

            if not valid_items:
                messages.error(request, "يجب إضافة بند واحد على الأقل في عرض السعر")
                return _render_quotation_form(
                    request,
                    form=form,
                    item_formset=item_formset,
                    installment_formset=installment_formset,
                    page_title="إنشاء عرض سعر",
                )

            valid_installments = []
            for inst_form in installment_formset:
                if not hasattr(inst_form, "cleaned_data") or not inst_form.cleaned_data:
                    continue
                if inst_form.cleaned_data.get("DELETE", False):
                    continue
                valid_installments.append(inst_form)

            total_percentage = sum(
                (inst_form.cleaned_data.get("percentage") or 0)
                for inst_form in valid_installments
            )

            if valid_installments and total_percentage != 100:
                messages.error(request, "مجموع نسب الدفعات يجب أن يساوي 100%")
                return _render_quotation_form(
                    request,
                    form=form,
                    item_formset=item_formset,
                    installment_formset=installment_formset,
                    page_title="إنشاء عرض سعر",
                )

            with transaction.atomic():
                quotation = form.save(commit=False)
                quotation.institution = institution
                quotation.executive = request.user
                quotation.save()

                item_formset.instance = quotation
                item_formset.save()

                quotation.calculate_totals()

                installment_formset.instance = quotation
                installment_formset.save()

                for installment in quotation.installments.all():
                    installment.save()

            messages.success(request, "تم إنشاء عرض السعر بنجاح")
            return redirect("quotation_detail", quotation_id=quotation.id)

        messages.error(request, "تعذر إنشاء عرض السعر، راجع الأخطاء الظاهرة في النموذج")

    else:
        form = PriceQuotationForm(institution=institution)
        item_formset = PriceQuotationItemFormSet(prefix="items")
        installment_formset = PriceQuotationInstallmentFormSet(prefix="installments")

    return _render_quotation_form(
        request,
        form=form,
        item_formset=item_formset,
        installment_formset=installment_formset,
        page_title="إنشاء عرض سعر",
    )


@login_required
def quotation_detail_view(request, quotation_id):
    quotation = get_object_or_404(
        PriceQuotation.objects.select_related(
            "institution",
            "executive",
            "client",
        ).prefetch_related(
            "items",
            "installments",
        ),
        id=quotation_id,
    )

    if not _can_access_quotation(request.user, quotation):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    return render(
        request,
        "quotations/quotation_detail.html",
        {
            "quotation": quotation,
            "user_type_label": "عروض الأسعار",
        },
    )


@login_required
def quotation_print_view(request, quotation_id):
    quotation = get_object_or_404(
        PriceQuotation.objects.select_related(
            "institution",
            "executive",
            "client",
        ).prefetch_related(
            "items",
            "installments",
        ),
        id=quotation_id,
    )

    if not _can_access_quotation(request.user, quotation):
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    return render(
        request,
        "quotations/quotation_print.html",
        {
            "quotation": quotation,
        },
    )


@login_required
def quotation_client_decision_view(request, quotation_id):
    if request.user.user_type != "client":
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    quotation = get_object_or_404(
        PriceQuotation.objects.select_related(
            "institution",
            "executive",
            "client",
        ).prefetch_related(
            "items",
            "installments",
        ),
        id=quotation_id,
        client=request.user,
    )

    if request.method == "POST":
        decision = request.POST.get("decision")
        client_note = request.POST.get("client_decision_note", "").strip()

        if decision == "accept":
            quotation.status = "accepted"
            quotation.client_decision_note = client_note
            quotation.save(update_fields=["status", "client_decision_note"])
            messages.success(request, "تم قبول عرض السعر بنجاح، اختر طريقة الدفع")
            return redirect("quotation_payment_choice", quotation_id=quotation.id)

        if decision == "reject":
            quotation.status = "rejected"
            quotation.client_decision_note = client_note
            quotation.save(update_fields=["status", "client_decision_note"])
            messages.success(request, "تم رفض عرض السعر")
            return redirect("quotation_detail", quotation_id=quotation.id)

        messages.error(request, "الرجاء اختيار قرار صحيح")

    return render(
        request,
        "quotations/quotation_client_decision.html",
        {
            "quotation": quotation,
            "user_type_label": "عروض الأسعار",
        },
    )


@login_required
def quotation_payment_choice_view(request, quotation_id):
    if request.user.user_type != "client":
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    quotation = get_object_or_404(
        PriceQuotation.objects.select_related(
            "institution",
            "executive",
            "client",
        ).prefetch_related(
            "items",
            "installments",
        ),
        id=quotation_id,
        client=request.user,
    )

    if quotation.status != "accepted":
        messages.error(request, "يجب قبول عرض السعر أولاً")
        return redirect("quotation_detail", quotation_id=quotation.id)

    if request.method == "POST":
        payment_method = request.POST.get("payment_method")

        if payment_method not in ["platform_card", "bank_transfer", "cash"]:
            messages.error(request, "الرجاء اختيار طريقة دفع صحيحة")
            return render(
                request,
                "quotations/quotation_payment_choice.html",
                {
                    "quotation": quotation,
                    "user_type_label": "عروض الأسعار",
                },
            )

        quotation.payment_method = payment_method
        quotation.save(update_fields=["payment_method"])

        messages.success(request, "تم حفظ طريقة الدفع بنجاح")
        return redirect("quotation_detail", quotation_id=quotation.id)

    return render(
        request,
        "quotations/quotation_payment_choice.html",
        {
            "quotation": quotation,
            "user_type_label": "عروض الأسعار",
        },
    )
