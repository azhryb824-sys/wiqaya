@login_required
def contract_edit_view(request, contract_id):
    contract = get_contract_for_user_or_404(request.user, contract_id)

    # فقط المدير التنفيذي أو المساعد الإداري يقدر يعدل
    if request.user.user_type not in ["executive", "admin_assistant"]:
        return HttpResponseForbidden("غير مصرح لك")

    institution = get_user_institution(request.user)

    form = MaintenanceContractForm(
        request.POST or None,
        instance=contract,
        institution=institution
    )

    if request.method == "POST":
        if form.is_valid():
            updated_contract = form.save(commit=False)
            updated_contract.institution = institution
            updated_contract.executive = request.user
            updated_contract.save()

            messages.success(request, "تم تعديل العقد بنجاح")
            return redirect("contract_detail", contract_id=contract.id)

        messages.error(request, "حدث خطأ أثناء التعديل، راجع البيانات")

    return render(
        request,
        "contracts/contract_form.html",  # نفس صفحة الإنشاء
        {
            "form": form,
            "contract": contract,
            "is_edit": True,
        },
    )
