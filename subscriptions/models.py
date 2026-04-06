from datetime import timedelta
from django.db import models
from django.utils import timezone


class SubscriptionPlan(models.Model):
    PLAN_TYPES = (
        ("contracts_certificates", "إدارة العقود وشهادات إنهاء الأعمال"),
        ("full", "الباقة الشاملة"),
    )

    BILLING_CYCLES = (
        ("monthly", "شهري"),
        ("yearly", "سنوي"),
    )

    name = models.CharField(max_length=200, verbose_name="اسم الخطة")
    plan_type = models.CharField(max_length=50, choices=PLAN_TYPES, verbose_name="نوع الخطة")
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CYCLES, verbose_name="دورية الدفع")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر")
    is_active = models.BooleanField(default=True, verbose_name="نشطة")

    allow_contracts = models.BooleanField(default=True, verbose_name="يسمح بالعقود")
    allow_certificates = models.BooleanField(default=True, verbose_name="يسمح بالشهادات")
    allow_visits = models.BooleanField(default=False, verbose_name="يسمح بالزيارات")
    allow_quotations = models.BooleanField(default=False, verbose_name="يسمح بعروض الأسعار")

    duration_days = models.PositiveIntegerField(verbose_name="عدد الأيام")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "خطة اشتراك"
        verbose_name_plural = "خطط الاشتراك"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} - {self.get_billing_cycle_display()}"


class InstitutionSubscription(models.Model):
    institution = models.OneToOneField(
        "core.Institution",
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="المؤسسة",
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
        verbose_name="الخطة",
    )
    start_date = models.DateTimeField(default=timezone.now, verbose_name="تاريخ البداية")
    end_date = models.DateTimeField(verbose_name="تاريخ النهاية")
    is_active = models.BooleanField(default=True, verbose_name="مفعل")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "اشتراك مؤسسة"
        verbose_name_plural = "اشتراكات المؤسسات"

    def __str__(self):
        return f"{self.institution} - {self.plan}"

    def is_valid(self):
        return self.is_active and self.plan is not None and self.end_date >= timezone.now()

    def is_expired(self):
        return self.end_date < timezone.now()


def default_subscription_end(days=30):
    return timezone.now() + timedelta(days=days)
