from django import forms
from .models import MaintenanceContract, ContractClauseTemplate
from core.models import User


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
            "client",
            "client_identifier",
            "second_party_name",
            "building_name",
            "activity",
            "building_location",
            "duration_years",
            "start_date",
            "clause_templates",
        ]
        widgets = {
            "contract_number": forms.TextInput(attrs={"class": "form-control"}),
            "client": forms.Select(attrs={"class": "form-select"}),
            "client_identifier": forms.TextInput(attrs={"class": "form-control"}),
            "second_party_name": forms.TextInput(attrs={"class": "form-control"}),
            "building_name": forms.TextInput(attrs={"class": "form-control"}),
            "activity": forms.TextInput(attrs={"class": "form-control"}),
            "building_location": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "duration_years": forms.Select(attrs={"class": "form-select"}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        labels = {
            "contract_number": "رقم العقد",
            "client": "العميل",
            "client_identifier": "معرف العميل",
            "second_party_name": "اسم الطرف الثاني",
            "building_name": "اسم المبنى",
            "activity": "النشاط",
            "building_location": "موقع المبنى",
            "duration_years": "مدة العقد",
            "start_date": "تاريخ بداية العقد (ميلادي)",
        }

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop("institution", None)
        super().__init__(*args, **kwargs)

        if institution:
            self.fields["client"].queryset = institution.users.filter(
                user_type="client"
            )
            self.fields["clause_templates"].queryset = institution.contract_clause_templates.filter(
                is_active=True
            ).order_by("order", "id")
        else:
            self.fields["client"].queryset = User.objects.filter(user_type="client")
            self.fields["clause_templates"].queryset = ContractClauseTemplate.objects.filter(
                is_active=True
            ).order_by("order", "id")

        self.fields["client"].required = False
        self.fields["client_identifier"].required = False
        self.fields["activity"].required = False
        self.fields["building_location"].required = False

    def clean_contract_number(self):
        contract_number = self.cleaned_data["contract_number"]
        qs = MaintenanceContract.objects.filter(contract_number=contract_number)

        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("رقم العقد مستخدم من قبل.")
        return contract_number


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
