from django import forms
from contracts.models import MaintenanceContract
from .models import CompletionCertificate, CertificateClauseTemplate
from hijridate import Gregorian


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
        return ""
    hijri = Gregorian(date_obj.year, date_obj.month, date_obj.day).to_hijri()
    month_name = ARABIC_HIJRI_MONTHS.get(hijri.month, str(hijri.month))
    return f"{hijri.day} {month_name} {hijri.year}هـ"


class CompletionCertificateForm(forms.ModelForm):
    contract = forms.ModelChoiceField(
        queryset=MaintenanceContract.objects.none(),
        required=True,
        label="العقد",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    clause_templates = forms.ModelMultipleChoiceField(
        queryset=CertificateClauseTemplate.objects.none(),
        required=False,
        label="بنود الشهادة",
        widget=forms.CheckboxSelectMultiple,
    )

    expiry_date_hijri = forms.CharField(
        required=False,
        label="تاريخ الانتهاء (هجري - أم القرى)",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "readonly": "readonly",
            }
        ),
    )

    class Meta:
        model = CompletionCertificate
        fields = [
            "certificate_number",
            "contract",
            "beneficiary_name",
            "owner_name",
            "building_name",
            "activity",
            "building_location",
            "issue_date",
            "notes",
            "clause_templates",
        ]
        widgets = {
            "certificate_number": forms.TextInput(attrs={"class": "form-control"}),
            "beneficiary_name": forms.TextInput(attrs={"class": "form-control"}),
            "owner_name": forms.TextInput(attrs={"class": "form-control"}),
            "building_name": forms.TextInput(attrs={"class": "form-control"}),
            "activity": forms.TextInput(attrs={"class": "form-control"}),
            "building_location": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "issue_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop("institution", None)
        fixed_contract = kwargs.pop("fixed_contract", None)
        super().__init__(*args, **kwargs)

        if institution:
            self.fields["contract"].queryset = MaintenanceContract.objects.filter(
                institution=institution
            ).order_by("-id")

            templates = institution.certificate_clause_templates.filter(
                is_active=True
            ).order_by("clause_type", "order", "id")
            self.fields["clause_templates"].queryset = templates
        else:
            self.fields["contract"].queryset = MaintenanceContract.objects.none()
            templates = CertificateClauseTemplate.objects.filter(
                is_active=True
            ).order_by("clause_type", "order", "id")
            self.fields["clause_templates"].queryset = templates

        if fixed_contract:
            self.fields["contract"].initial = fixed_contract
            self.fields["contract"].queryset = MaintenanceContract.objects.filter(id=fixed_contract.id)
            self.fields["contract"].widget = forms.HiddenInput()

            if not self.initial.get("beneficiary_name"):
                self.initial["beneficiary_name"] = fixed_contract.second_party_name

            if not self.initial.get("building_name"):
                self.initial["building_name"] = fixed_contract.building_name

            if not self.initial.get("building_location"):
                self.initial["building_location"] = fixed_contract.building_location

            self.fields["expiry_date_hijri"].initial = format_hijri(fixed_contract.end_date)

        elif self.instance and self.instance.pk and self.instance.expiry_date:
            self.fields["expiry_date_hijri"].initial = format_hijri(self.instance.expiry_date)

        for template in self.fields["clause_templates"].queryset:
            self.fields[f"work_type_{template.id}"] = forms.ChoiceField(
                choices=[
                    ("installation", "تركيب"),
                    ("maintenance", "صيانة"),
                ],
                required=False,
                label=f"نوع العقد للبند: {template.title}",
                widget=forms.Select(attrs={"class": "form-select"}),
            )

    def clean(self):
        cleaned_data = super().clean()
        contract = cleaned_data.get("contract")
        selected_templates = cleaned_data.get("clause_templates")

        if contract:
            if not cleaned_data.get("beneficiary_name"):
                cleaned_data["beneficiary_name"] = contract.second_party_name

            if not cleaned_data.get("building_name"):
                cleaned_data["building_name"] = contract.building_name

            if not cleaned_data.get("building_location"):
                cleaned_data["building_location"] = contract.building_location

        if selected_templates:
            for template in selected_templates:
                work_type = cleaned_data.get(f"work_type_{template.id}")
                if not work_type:
                    self.add_error(
                        f"work_type_{template.id}",
                        f"يجب اختيار نوع العقد للبند: {template.title}"
                    )

        return cleaned_data


class CertificateClauseTemplateForm(forms.ModelForm):
    class Meta:
        model = CertificateClauseTemplate
        fields = [
            "clause_type",
            "title",
            "details",
            "order",
            "is_active",
        ]
        labels = {
            "clause_type": "نوع البند",
            "title": "اسم البند",
            "details": "التفاصيل",
            "order": "الترتيب",
            "is_active": "نشط",
        }
        widgets = {
            "clause_type": forms.Select(attrs={"class": "form-select"}),
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "مثال: طفايات الحريق"}),
            "details": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "أدخل وصفاً مختصراً للبند"}),
            "order": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }