from datetime import date

from django.db import models
from hijridate import Gregorian, Hijri

from core.models import User, Institution


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


def format_hijri_date(hijri_obj):
    month_name = ARABIC_HIJRI_MONTHS.get(hijri_obj.month, str(hijri_obj.month))
    return f"{hijri_obj.day} {month_name} {hijri_obj.year}هـ"


class ContractClauseTemplate(models.Model):
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="contract_clause_templates",
        verbose_name="المؤسسة"
    )
    title = models.CharField(max_length=255, verbose_name="عنوان البند")
    content = models.TextField(verbose_name="نص البند")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "قالب بند عقد"
        verbose_name_plural = "قوالب بنود العقود"

    def __str__(self):
        return self.title


class MaintenanceContract(models.Model):
    DURATION_CHOICES = (
        (1, "عام"),
        (2, "عامان"),
        (3, "3 أعوام"),
        (4, "4 أعوام"),
        (5, "5 أعوام"),
    )

    contract_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="رقم العقد"
    )
    client = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_contracts",
        verbose_name="العميل"
    )
    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="contracts",
        verbose_name="المؤسسة"
    )
    executive = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executive_contracts",
        verbose_name="المدير التنفيذي"
    )

    second_party_name = models.CharField(
        max_length=255,
        verbose_name="اسم الطرف الثاني"
    )
    building_name = models.CharField(
        max_length=255,
        verbose_name="اسم المبنى"
    )
    activity = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="النشاط"
    )
    building_location = models.TextField(
        blank=True,
        null=True,
        verbose_name="موقع المبنى"
    )
    client_identifier = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="معرف العميل"
    )

    duration_years = models.PositiveSmallIntegerField(
        choices=DURATION_CHOICES,
        default=1,
        verbose_name="مدة العقد"
    )

    # يدخل من المستخدم بالميلادي
    start_date = models.DateField(verbose_name="تاريخ البداية")

    # يتحسب تلقائياً من التاريخ الهجري للبداية
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="تاريخ النهاية"
    )

    # حقول هجري للعرض والطباعة
    start_date_hijri = models.CharField(
        max_length=50,
        blank=True,
        editable=False,
        verbose_name="تاريخ البداية هجري"
    )
    end_date_hijri = models.CharField(
        max_length=50,
        blank=True,
        editable=False,
        verbose_name="تاريخ النهاية هجري"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "عقد صيانة"
        verbose_name_plural = "عقود الصيانة"

    def __str__(self):
        return f"{self.contract_number} - {self.second_party_name}"

    def calculate_dates(self):
        if not self.start_date:
            return

        # تحويل البداية الميلادية إلى هجري
        start_hijri = Gregorian(
            self.start_date.year,
            self.start_date.month,
            self.start_date.day
        ).to_hijri()

        self.start_date_hijri = format_hijri_date(start_hijri)

        # حساب نهاية العقد على أساس التاريخ الهجري
        end_hijri = Hijri(
            start_hijri.year + int(self.duration_years),
            start_hijri.month,
            start_hijri.day
        )

        self.end_date_hijri = format_hijri_date(end_hijri)

        # تحويل النهاية الهجرية إلى ميلادي للتخزين الداخلي
        end_gregorian = end_hijri.to_gregorian()
        self.end_date = date(
            end_gregorian.year,
            end_gregorian.month,
            end_gregorian.day
        )

    def save(self, *args, **kwargs):
        self.calculate_dates()
        super().save(*args, **kwargs)


class MaintenanceContractClause(models.Model):
    contract = models.ForeignKey(
        MaintenanceContract,
        on_delete=models.CASCADE,
        related_name="clauses",
        verbose_name="العقد"
    )
    title = models.CharField(max_length=255, verbose_name="عنوان البند")
    content = models.TextField(verbose_name="نص البند")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "بند عقد"
        verbose_name_plural = "بنود العقود"

    def __str__(self):
        return f"{self.contract.contract_number} - {self.title}"
