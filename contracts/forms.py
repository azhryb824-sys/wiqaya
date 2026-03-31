from django import forms
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
        widgets = {
            "contract_number": forms.TextInput(attrs={"class": "form-control"}),
            "client_identifier": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "أدخل رقم هوية العميل أو الرقم الموحد للمنشأة",
                "dir": "ltr",
            }),
            "second_party_name": forms.TextInput(attrs={
                "class": "form-control",
                "readonly": "readonly",
            }),
            "building_name": forms.TextInput(attrs={"class": "form-control"}),
            "activity": forms.TextInput(attrs={"class": "form-control"}),
            "building_location": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "google_maps_url": forms.URLInput(attrs={
                "class": "form-control",
                "placeholder": "https://maps.google.com/...",
                "dir": "ltr",
            }),
            "duration_years": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        labels = {
            "contract_number": "رقم العقد",
            "client_identifier": "رقم هوية العميل أو الرقم الموحد للمنشأة",
            "second_party_name": "اسم الطرف الثاني",
            "building_name": "اسم المبنى",
            "activity": "النشاط",
            "building_location": "موقع المبنى",
            "google_maps_url": "رابط موقع المبنى في خرائط جوجل",
            "duration_years": "مدة العقد",
            "start_date": "تاريخ بداية العقد (ميلادي)",
        }
        help_texts = {
            "client_identifier": "أدخل رقم هوية العميل أو الرقم الموحد للمنشأة، وسيتم الربط تلقائياً عند حفظ العقد.",
            "second_party_name": "يُعبأ تلقائياً باسم المنشأة عند إدخال الرقم الموحد، أو باسم العميل عند إدخال رقم الهوية.",
            "google_maps_url": "أدخل رابط موقع المبنى من خرائط جوجل ليظهر رابط الموقع في الزيارة وسجل الزيارات.",
        }

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop("institution", None)
        super().__init__(*args, **kwargs)

        if institution:
            self.fields["clause_templates"].queryset = institution.contract_clause_templates.filter(
                is_active=True
            ).order_by("order", "id")
        else:
            self.fields["clause_templates"].queryset = ContractClauseTemplate.objects.filter(
                is_active=True
            ).order_by("order", "id")

        self.fields["client_identifier"].required = False
        self.fields["second_party_name"].required = False
        self.fields["activity"].required = False
        self.fields["building_location"].required = False
        self.fields["google_maps_url"].required = False

    def clean_contract_number(self):
        contract_number = self.cleaned_data["contract_number"]
        qs = MaintenanceContract.objects.filter(contract_number=contract_number)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("رقم العقد مستخدم من قبل.")
        return contract_number

    def clean_google_maps_url(self):
        google_maps_url = self.cleaned_data.get("google_maps_url")

        if google_maps_url:
            allowed_domains = [
                "google.com",
                "maps.google.com",
                "maps.app.goo.gl",
                "goo.gl",
            ]
            if not any(domain in google_maps_url for domain in allowed_domains):
                raise forms.ValidationError("الرجاء إدخال رابط صحيح من خرائط جوجل.")

        return google_maps_url


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
