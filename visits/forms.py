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
        ]
        labels = {
            "contract": "العقد",
            "technician": "الفني",
            "visit_date": "تاريخ الزيارة",
        }
        widgets = {
            "contract": forms.Select(attrs={"class": "form-select"}),
            "technician": forms.Select(attrs={"class": "form-select"}),
            "visit_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
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
        fields = [
            "notes",
            "extinguishers_expiry_hijri",
        ]
        labels = {
            "notes": "ملاحظات الفني",
            "extinguishers_expiry_hijri": "تاريخ انتهاء الطفايات (هجري)",
        }
        widgets = {
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "extinguishers_expiry_hijri": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "مثال: 15 شوال 1447هـ",
            }),
        }

    def clean_extinguishers_expiry_hijri(self):
        value = (self.cleaned_data.get("extinguishers_expiry_hijri") or "").strip()
        return value
