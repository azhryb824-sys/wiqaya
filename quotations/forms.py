from django import forms
from django.forms import inlineformset_factory

from core.models import User
from .models import PriceQuotation, PriceQuotationItem, PriceQuotationInstallment


# =========================
# عرض السعر
# =========================
class PriceQuotationForm(forms.ModelForm):
    class Meta:
        model = PriceQuotation
        fields = [
            "quotation_number",
            "client",
            "client_display_name",
            "building_name",
            "building_location",
            "payment_terms",
            "execution_days",
            "institution_account_number",
            "status",
        ]
        labels = {
            "quotation_number": "رقم عرض السعر",
            "client": "العميل",
            "client_display_name": "مؤسسة العميل",
            "building_name": "اسم المبنى",
            "building_location": "موقع المبنى",
            "payment_terms": "طريقة الدفع",
            "execution_days": "عدد أيام التنفيذ",
            "institution_account_number": "رقم حساب المؤسسة",
            "status": "الحالة",
        }
        widgets = {
            "quotation_number": forms.TextInput(attrs={"class": "form-control"}),
            "client": forms.Select(attrs={"class": "form-select"}),
            "client_display_name": forms.TextInput(attrs={"class": "form-control"}),
            "building_name": forms.TextInput(attrs={"class": "form-control"}),
            "building_location": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "payment_terms": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "مثال: 50% دفعة أولى عند التعميد، 30% عند التوريد، 20% عند التسليم"
                }
            ),
            "execution_days": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "مثال: 16"
                }
            ),
            "institution_account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "رقم حساب المؤسسة / الآيبان"
                }
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        institution = kwargs.pop("institution", None)
        super().__init__(*args, **kwargs)

        if institution:
            self.fields["client"].queryset = institution.users.filter(user_type="client")
        else:
            self.fields["client"].queryset = User.objects.filter(user_type="client")

    def clean_quotation_number(self):
        quotation_number = self.cleaned_data["quotation_number"].strip()
        qs = PriceQuotation.objects.filter(quotation_number=quotation_number)

        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("رقم عرض السعر مستخدم مسبقاً")

        return quotation_number

    def clean_execution_days(self):
        execution_days = self.cleaned_data.get("execution_days")
        if execution_days is not None and execution_days <= 0:
            raise forms.ValidationError("عدد أيام التنفيذ يجب أن يكون أكبر من صفر")
        return execution_days


# =========================
# بنود العرض
# =========================
class PriceQuotationItemForm(forms.ModelForm):
    class Meta:
        model = PriceQuotationItem
        fields = ["description", "quantity", "unit_price", "order"]
        labels = {
            "description": "الإيضاحات",
            "quantity": "الكمية",
            "unit_price": "السعر الفرادي",
            "order": "الترتيب",
        }
        widgets = {
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
            "unit_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "order": forms.NumberInput(attrs={"class": "form-control"}),
        }


# =========================
# الدفعات
# =========================
class PriceQuotationInstallmentForm(forms.ModelForm):
    class Meta:
        model = PriceQuotationInstallment
        fields = ["title", "percentage", "due_description"]
        labels = {
            "title": "اسم الدفعة",
            "percentage": "النسبة %",
            "due_description": "موعد الدفع",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "percentage": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "due_description": forms.TextInput(attrs={"class": "form-control"}),
        }


# =========================
# FormSets
# =========================
PriceQuotationItemFormSet = inlineformset_factory(
    PriceQuotation,
    PriceQuotationItem,
    form=PriceQuotationItemForm,
    extra=3,
    can_delete=True,
)

PriceQuotationInstallmentFormSet = inlineformset_factory(
    PriceQuotation,
    PriceQuotationInstallment,
    form=PriceQuotationInstallmentForm,
    extra=2,
    can_delete=True,
)