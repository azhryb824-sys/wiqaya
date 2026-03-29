from django.db import models
from core.models import Institution, User
from contracts.models import MaintenanceContract


class CertificateClauseTemplate(models.Model):
    CLAUSE_TYPES = (
        ("safety_tools", "وسائل السلامة المتوفرة"),
        ("fire_system", "نظام الإطفاء"),
    )

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="certificate_clause_templates",
        verbose_name="المؤسسة",
    )
    clause_type = models.CharField(
        max_length=30,
        choices=CLAUSE_TYPES,
        verbose_name="نوع البند",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="اسم البند",
    )
    details = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="تفاصيل إضافية",
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="الترتيب",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
    )

    class Meta:
        ordering = ["clause_type", "order", "id"]
        verbose_name = "قالب بند شهادة"
        verbose_name_plural = "قوالب بنود الشهادات"

    def __str__(self):
        return self.title


class CompletionCertificate(models.Model):
    WORK_TYPES = (
        ("installation", "تركيب"),
        ("maintenance", "صيانة"),
    )

    certificate_number = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="رقم الشهادة",
    )

    contract = models.ForeignKey(
        MaintenanceContract,
        on_delete=models.CASCADE,
        related_name="completion_certificates",
        verbose_name="العقد",
        null=True,
        blank=True,
    )

    client = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completion_certificates",
        verbose_name="العميل",
        limit_choices_to={"user_type": "client"},
    )

    institution = models.ForeignKey(
        Institution,
        on_delete=models.CASCADE,
        related_name="certificates",
        verbose_name="المؤسسة",
    )

    executive = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executive_certificates",
        verbose_name="المدير التنفيذي",
    )

    work_type = models.CharField(
        max_length=30,
        choices=WORK_TYPES,
        verbose_name="نوع العمل",
        default="maintenance",
    )

    beneficiary_name = models.CharField(
        max_length=255,
        verbose_name="اسم المستفيد",
    )
    owner_name = models.CharField(
        max_length=255,
        verbose_name="اسم المالك",
    )
    building_name = models.CharField(
        max_length=255,
        verbose_name="اسم المبنى",
    )
    activity = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="النشاط",
    )
    building_location = models.TextField(
        blank=True,
        null=True,
        verbose_name="موقع المبنى",
    )
    issue_date = models.DateField(
        verbose_name="تاريخ الإصدار",
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="تاريخ الانتهاء",
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="ملاحظات",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "شهادة إنهاء أعمال"
        verbose_name_plural = "شهادات إنهاء الأعمال"

    def save(self, *args, **kwargs):
        if self.contract:
            if not self.client:
                self.client = self.contract.client

            if not self.institution_id:
                self.institution = self.contract.institution

            if not self.building_name:
                self.building_name = self.contract.building_name

            if not self.building_location:
                self.building_location = self.contract.building_location

            if not self.beneficiary_name:
                self.beneficiary_name = self.contract.second_party_name

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.certificate_number} - {self.beneficiary_name}"


class CompletionCertificateClause(models.Model):
    CLAUSE_TYPES = (
        ("safety_tools", "وسائل السلامة المتوفرة"),
        ("fire_system", "نظام الإطفاء"),
    )

    WORK_TYPES = (
        ("installation", "تركيب"),
        ("maintenance", "صيانة"),
    )

    certificate = models.ForeignKey(
        CompletionCertificate,
        on_delete=models.CASCADE,
        related_name="clauses",
        verbose_name="الشهادة",
    )
    clause_type = models.CharField(
        max_length=30,
        choices=CLAUSE_TYPES,
        verbose_name="نوع البند",
    )
    work_type = models.CharField(
        max_length=30,
        choices=WORK_TYPES,
        verbose_name="نوع العمل",
    )
    title = models.CharField(
        max_length=255,
        verbose_name="اسم البند",
    )
    details = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="تفاصيل إضافية",
    )
    contract_expiry_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="تاريخ انتهاء العقد",
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="الترتيب",
    )

    class Meta:
        ordering = ["clause_type", "order", "id"]
        verbose_name = "بند شهادة"
        verbose_name_plural = "بنود الشهادة"

    def __str__(self):
        return f"{self.certificate.certificate_number} - {self.title}"