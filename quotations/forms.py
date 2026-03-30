from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

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
            "quotation_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثال: QS-2026-001",
                }
            ),
            "client": forms.Select(attrs={"class": "form-select"}),
            "client_display_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "اسم مؤسسة العميل كما سيظهر في عرض السعر",
                }
            ),
            "building_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "اسم المبنى",
                }
            ),
            "building_location": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "أدخل موقع المبنى أو العنوان التفصيلي",
                }
            ),
            "payment_terms": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "مثال: 50% دفعة أولى عند التعميد، 30% عند التوريد، 20% عند التسليم",
                }
            ),
            "execution_days": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "placeholder": "مثال: 16",
                }
            ),
            "institution_account_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "رقم حساب المؤسسة / الآيبان",
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
        quotation_number = (self.cleaned_data.get("quotation_number") or "").strip()
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
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "اكتب وصف البند",
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
        }

    def clean_quantity(self):
        quantity = self.cleaned_data.get("quantity")
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("الكمية يجب أن تكون أكبر من صفر")
        return quantity

    def clean_unit_price(self):
        unit_price = self.cleaned_data.get("unit_price")
        if unit_price is not None and unit_price < 0:
            raise forms.ValidationError("السعر الفرادي لا يمكن أن يكون سالباً")
        return unit_price


class BasePriceQuotationItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        valid_items_count = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            description = (form.cleaned_data.get("description") or "").strip()
            quantity = form.cleaned_data.get("quantity")
            unit_price = form.cleaned_data.get("unit_price")

            if description or quantity or unit_price:
                valid_items_count += 1

            if description and quantity and unit_price is not None:
                continue

            if description or quantity or unit_price is not None:
                raise forms.ValidationError("يجب تعبئة وصف البند والكمية والسعر الفرادي لكل بند بشكل كامل.")

        if valid_items_count == 0:
            raise forms.ValidationError("يجب إضافة بند واحد على الأقل في عرض السعر.")


# =========================
# الدفعات
# =========================
class PriceQuotationInstallmentForm(forms.ModelForm):
    class Meta:
        model = PriceQuotationInstallment
        fields = ["title", "percentage", "due_description", "order"]
        labels = {
            "title": "اسم الدفعة",
            "percentage": "النسبة %",
            "due_description": "موعد الدفع",
            "order": "الترتيب",
        }
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثال: الدفعة الأولى",
                }
            ),
            "percentage": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "due_description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "مثال: عند التعميد",
                }
            ),
            "order": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
        }

    def clean_percentage(self):
        percentage = self.cleaned_data.get("percentage")
        if percentage is not None and percentage < 0:
            raise forms.ValidationError("النسبة لا يمكن أن تكون سالبة")
        return percentage


class BasePriceQuotationInstallmentFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        total_percentage = 0

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue

            if form.cleaned_data.get("DELETE"):
                continue

            title = (form.cleaned_data.get("title") or "").strip()
            percentage = form.cleaned_data.get("percentage")
            due_description = (form.cleaned_data.get("due_description") or "").strip()

            if title or percentage is not None or due_description:
                if not title or percentage is None or not due_description:
                    raise forms.ValidationError("يجب تعبئة جميع بيانات الدفعة أو تركها فارغة بالكامل.")

                total_percentage += percentage

        if total_percentage and total_percentage != 100:
            raise forms.ValidationError("إجمالي نسب الدفعات يجب أن يساوي 100%.")


# =========================
# FormSets
# =========================
PriceQuotationItemFormSet = inlineformset_factory(
    PriceQuotation,
    PriceQuotationItem,
    form=PriceQuotationItemForm,
    formset=BasePriceQuotationItemFormSet,
    extra=1,
    can_delete=True,
)

PriceQuotationInstallmentFormSet = inlineformset_factory(
    PriceQuotation,
    PriceQuotationInstallment,
    form=PriceQuotationInstallmentForm,
    formset=BasePriceQuotationInstallmentFormSet,
    extra=1,
    can_delete=True,
)
