from django import forms
from .models import Visit
from core.models import User
from contracts.models import MaintenanceContract


class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = [
            "contract",
            "technician",
            "visit_date",
            "month_label",
            "notes",
        ]
        widgets = {
            "contract": forms.Select(attrs={"class": "form-select"}),
            "technician": forms.Select(attrs={"class": "form-select"}),
            "visit_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "month_label": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop("institution", None)
        super().__init__(*args, **kwargs)

        if institution:
            self.fields["contract"].queryset = institution.contracts.all()
            self.fields["technician"].queryset = institution.users.filter(user_type="technician")
        else:
            self.fields["contract"].queryset = MaintenanceContract.objects.none()
            self.fields["technician"].queryset = User.objects.filter(user_type="technician")


class VisitNoteForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ["notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }