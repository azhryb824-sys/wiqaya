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
            "building_location",
            "start_date",
            "end_date",
            "clause_templates",
        ]
        widgets = {
            "contract_number": forms.TextInput(attrs={"class": "form-control"}),
            "client": forms.Select(attrs={"class": "form-select"}),
            "client_identifier": forms.TextInput(attrs={"class": "form-control"}),
            "second_party_name": forms.TextInput(attrs={"class": "form-control"}),
            "building_name": forms.TextInput(attrs={"class": "form-control"}),
            "building_location": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "end_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop("institution", None)
        super().__init__(*args, **kwargs)

        if institution:
            self.fields["client"].queryset = institution.users.filter(user_type="client")
            self.fields["clause_templates"].queryset = institution.contract_clause_templates.filter(is_active=True)
        else:
            self.fields["client"].queryset = User.objects.filter(user_type="client")
            self.fields["clause_templates"].queryset = ContractClauseTemplate.objects.filter(is_active=True)


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