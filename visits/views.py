# ================================
# تعديل الزيارة (للمدير التنفيذي فقط)
# ================================
@login_required
def visit_edit_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    # صلاحية المدير التنفيذي فقط
    if request.user.user_type != "executive":
        messages.error(request, "غير مصرح لك بتعديل هذه الزيارة")
        return redirect("visit_list")

    # منع التعديل بعد الاعتماد
    if visit.technician_approved or visit.client_approved:
        messages.error(request, "لا يمكن تعديل الزيارة بعد اعتمادها")
        return redirect("visit_detail", visit_id=visit.id)

    institution = _get_user_institution(request.user)

    form = VisitForm(request.POST or None, instance=visit, institution=institution)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل الزيارة بنجاح")
            return redirect("visit_detail", visit_id=visit.id)

        print(form.errors)
        messages.error(request, "تعذر تعديل الزيارة، راجع الأخطاء")

    return render(
        request,
        "visits/visit_form.html",
        {
            "form": form,
            "visit": visit,
            "is_edit": True,
            "user_type_label": "الزيارات",
        },
    )


# ================================
# حذف الزيارة (للمدير التنفيذي فقط)
# ================================
@login_required
def visit_delete_view(request, visit_id):
    visit = get_object_or_404(Visit, id=visit_id)

    # صلاحية المدير التنفيذي فقط
    if request.user.user_type != "executive":
        messages.error(request, "غير مصرح لك بحذف هذه الزيارة")
        return redirect("visit_list")

    # منع الحذف بعد الاعتماد
    if visit.technician_approved or visit.client_approved:
        messages.error(request, "لا يمكن حذف الزيارة بعد اعتمادها")
        return redirect("visit_detail", visit_id=visit.id)

    if request.method == "POST":
        contract_id = visit.contract.id
        visit.delete()
        messages.success(request, "تم حذف الزيارة بنجاح")
        return redirect("contract_visits_log", contract_id=contract_id)

    return render(
        request,
        "visits/visit_confirm_delete.html",
        {
            "visit": visit,
            "user_type_label": "الزيارات",
        },
    )
