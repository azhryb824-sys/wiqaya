from django import forms
from django.core.exceptions import ValidationError
from urllib.parse import urlparse

from .models import MaintenanceContract, ContractClauseTemplate


class MaintenanceContractForm(forms.ModelForm):
    clause_templates = forms.ModelMultipleChoiceField(
        queryset=ContractClauseTemplate.objects.none(),
        required=False,
        label="بنود العقد",
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = MaintenanceContract
        fields = [
            "contract_number",
            "client_identifier",
            "second_party_name",
            "building_name",
            "activity",
            "building_location",
            "google_maps_url",
            "duration_years",
            "start_date",
            "clause_templates",
        ]

    def __init__(self, *args, **kwargs):
        self.institution = kwargs.pop("institution", None)
        super().__init__(*args, **kwargs)

        # ✅ فقط البنود تكون من نفس المؤسسة (هذا مهم للأمان)
        if self.institution:
            self.allowed_templates = self.institution.contract_clause_templates.filter(
                is_active=True
            ).order_by("order", "id")
        else:
            self.allowed_templates = ContractClauseTemplate.objects.filter(
                is_active=True
            ).order_by("order", "id")

        self.fields["clause_templates"].queryset = self.allowed_templates

        # optional fields
        self.fields["client_identifier"].required = False
        self.fields["second_party_name"].required = False
        self.fields["activity"].required = False
        self.fields["building_location"].required = False
        self.fields["google_maps_url"].required = False

    # -----------------------
    # رقم العقد
    # -----------------------
    def clean_contract_number(self):
        contract_number = (self.cleaned_data["contract_number"] or "").strip()

        qs = MaintenanceContract.objects.filter(contract_number=contract_number)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise ValidationError("رقم العقد مستخدم من قبل.")

        return contract_number

    # -----------------------
    # Google Maps URL
    # -----------------------
    def clean_google_maps_url(self):
        url = self.cleaned_data.get("google_maps_url")

        if not url:
            return url

        parsed = urlparse(url)

        allowed_domains = [
            "google.com",
            "maps.google.com",
            "maps.app.goo.gl",
            "goo.gl",
        ]

        if not any(parsed.netloc.endswith(domain) for domain in allowed_domains):
            raise ValidationError("يجب إدخال رابط صحيح من خرائط جوجل.")

        if parsed.scheme not in ["http", "https"]:
            raise ValidationError("الرابط غير صالح.")

        return url

    # -----------------------
    # حماية البنود
    # -----------------------
    def clean_clause_templates(self):
        selected = self.cleaned_data.get("clause_templates")

        if not selected:
            return selected

        allowed_ids = set(self.allowed_templates.values_list("id", flat=True))

        for item in selected:
            if item.id not in allowed_ids:
                raise ValidationError("تم اختيار بند غير مصرح به.")

        return selected

    # -----------------------
    # تحقق عام
    # -----------------------
    def clean(self):
        cleaned_data = super().clean()

        identifier = (cleaned_data.get("client_identifier") or "").strip()
        second_name = (cleaned_data.get("second_party_name") or "").strip()
        duration = cleaned_data.get("duration_years")

        # ✅ لازم يكون في طرف ثاني (عميل أو اسم)
        if not identifier and not second_name:
            raise ValidationError("يجب إدخال رقم هوية/رقم موحد أو اسم الطرف الثاني.")

        # ✅ تحقق منطقي من المدة
        if duration and duration <= 0:
            raise ValidationError("مدة العقد غير صالحة.")

        return cleaned_data


class ContractClauseTemplateForm(forms.ModelForm):
    class Meta:
        model = ContractClauseTemplate
        fields = ["title", "content", "order", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
