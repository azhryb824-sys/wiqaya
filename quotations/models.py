from decimal import Decimal

from django.conf import settings
from django.db import models
from num2words import num2words

User = settings.AUTH_USER_MODEL


class PriceQuotation(models.Model):
    STATUS_CHOICES = [
        ("draft", "مسودة"),
        ("sent", "مرسل"),
        ("accepted", "مقبول"),
        ("rejected", "مرفوض"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("platform_card", "بطاقة عبر المنصة"),
        ("bank_transfer", "تحويل بنكي"),
        ("cash", "نقداً"),
    ]

    institution = models.ForeignKey(
        "core.Institution",
        on_delete=models.CASCADE,
        related_name="quotations",
        verbose_name="المؤسسة",
    )

    executive = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="executive_quotations",
        verbose_name="المدير التنفيذي",
    )

    client = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="client_quotations",
        verbose_name="العميل",
    )

    quotation_number = models.CharField(
        max_length=100,
        verbose_name="رقم عرض السعر",
    )

    client_display_name = models.CharField(
        max_length=255,
        verbose_name="اسم مؤسسة العميل",
    )

    building_name = models.CharField(
        max_length=255,
        verbose_name="اسم المبنى",
    )

    building_location = models.TextField(
        verbose_name="موقع المبنى",
    )

    issue_date = models.DateField(
        auto_now_add=True,
        verbose_name="تاريخ الإصدار",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="الحالة",
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_METHOD_CHOICES,
        blank=True,
        null=True,
        verbose_name="طريقة الدفع",
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المجموع",
    )

    vat_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="الضريبة",
    )

    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="الإجمالي",
    )

    grand_total_words = models.TextField(
        blank=True,
        null=True,
        verbose_name="المبلغ كتابة",
    )

    payment_terms = models.TextField(
        verbose_name="طريقة الدفع (الدفعات)",
    )

    execution_days = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد أيام التنفيذ",
    )

    execution_period = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="مدة التنفيذ",
    )

    institution_account_number = models.CharField(
        max_length=255,
        verbose_name="رقم حساب المؤسسة",
    )

    client_decision_note = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظة العميل",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-id"]
        verbose_name = "عرض سعر"
        verbose_name_plural = "عروض الأسعار"

    def __str__(self):
        return f"عرض سعر رقم {self.quotation_number}"

    def amount_to_arabic_words(self):
        amount = self.grand_total or Decimal("0.00")
        amount = amount.quantize(Decimal("0.01"))

        riyals = int(amount)
        halalas = int((amount - Decimal(riyals)) * 100)

        riyals_words = num2words(riyals, lang="ar")
        result = f"{riyals_words} ريال سعودي"

        if halalas > 0:
            halalas_words = num2words(halalas, lang="ar")
            result += f" و {halalas_words} هللة"

        return result

    def build_execution_period_text(self):
        if not self.execution_days:
            return ""

        first_installment = self.installments.order_by("order", "id").first()

        if first_installment and first_installment.title:
            return f"{self.execution_days} يوم عمل من تاريخ استلام الدفعة / {first_installment.title}"

        return f"{self.execution_days} يوم عمل من تاريخ استلام الدفعة الأولى"

    def update_installments_amounts(self):
        installments = self.installments.all()
        for installment in installments:
            installment.save()

    def calculate_totals(self, save=True):
        subtotal = sum(
            (item.total_price or Decimal("0.00")) for item in self.items.all()
        )
        vat = subtotal * Decimal("0.15")
        total = subtotal + vat

        self.subtotal = subtotal.quantize(Decimal("0.01"))
        self.vat_amount = vat.quantize(Decimal("0.01"))
        self.grand_total = total.quantize(Decimal("0.01"))
        self.grand_total_words = self.amount_to_arabic_words()
        self.execution_period = self.build_execution_period_text()

        if save and self.pk:
            self.save(
                update_fields=[
                    "subtotal",
                    "vat_amount",
                    "grand_total",
                    "grand_total_words",
                    "execution_period",
                ]
            )
            self.update_installments_amounts()

    @property
    def items_count(self):
        return self.items.count()


class PriceQuotationItem(models.Model):
    quotation = models.ForeignKey(
        PriceQuotation,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="عرض السعر",
    )

    description = models.TextField(
        verbose_name="الإيضاحات",
    )

    quantity = models.PositiveIntegerField(
        verbose_name="الكمية",
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="السعر الفرادي",
    )

    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="السعر الإجمالي",
        blank=True,
        null=True,
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="الترتيب",
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "بند عرض سعر"
        verbose_name_plural = "بنود عروض الأسعار"

    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        self.total_price = (Decimal(self.quantity) * self.unit_price).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)

        if self.quotation_id:
            self.quotation.calculate_totals()

    def delete(self, *args, **kwargs):
        quotation = self.quotation
        super().delete(*args, **kwargs)

        if quotation:
            quotation.calculate_totals()


class PriceQuotationInstallment(models.Model):
    quotation = models.ForeignKey(
        PriceQuotation,
        on_delete=models.CASCADE,
        related_name="installments",
        verbose_name="عرض السعر",
    )

    title = models.CharField(
        max_length=255,
        verbose_name="اسم الدفعة",
    )

    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="النسبة %",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="المبلغ",
        blank=True,
        null=True,
    )

    due_description = models.CharField(
        max_length=255,
        verbose_name="موعد الدفع",
    )

    order = models.PositiveIntegerField(
        default=0,
        verbose_name="الترتيب",
    )

    is_paid = models.BooleanField(
        default=False,
        verbose_name="تم السداد",
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "دفعة عرض سعر"
        verbose_name_plural = "دفعات عروض الأسعار"

    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.title}"

    def save(self, *args, **kwargs):
        if self.quotation and self.quotation.grand_total is not None:
            self.amount = (
                (self.percentage / Decimal("100")) * self.quotation.grand_total
            ).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)
