from django.db import models
from hijridate import Gregorian

from core.models import User
from contracts.models import MaintenanceContract


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


class Visit(models.Model):
    contract = models.ForeignKey(
        MaintenanceContract,
        on_delete=models.CASCADE,
        related_name="visits",
        verbose_name="العقد",
    )

    technician = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_visits",
        verbose_name="الفني",
    )

    visit_date = models.DateField(verbose_name="تاريخ الزيارة")

    month_label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="الشهر الهجري",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات الفني",
    )

    technician_approved = models.BooleanField(
        default=False,
        verbose_name="اعتماد الفني",
    )

    client_approved = models.BooleanField(
        default=False,
        verbose_name="اعتماد العميل",
    )

    technician_approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="وقت اعتماد الفني",
    )

    client_approved_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="وقت اعتماد العميل",
    )

    technician_signature = models.TextField(
        blank=True,
        null=True,
        verbose_name="توقيع الفني الإلكتروني",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-visit_date", "-id"]
        verbose_name = "زيارة"
        verbose_name_plural = "الزيارات"

    def save(self, *args, **kwargs):
        if self.visit_date:
            hijri = Gregorian(
                self.visit_date.year,
                self.visit_date.month,
                self.visit_date.day,
            ).to_hijri()
            month_name = ARABIC_HIJRI_MONTHS.get(hijri.month, str(hijri.month))
            self.month_label = f"{month_name} {hijri.year}هـ"

        super().save(*args, **kwargs)

    @property
    def status(self):
        if not self.technician_approved:
            return "بانتظار اعتماد الفني"
        if not self.client_approved:
            return "بانتظار اعتماد العميل"
        return "مكتملة"

    def __str__(self):
        return f"{self.contract.contract_number} - {self.visit_date}"