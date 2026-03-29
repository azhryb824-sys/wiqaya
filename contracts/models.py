from django.db import models
from core.models import User, Institution


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
    contract_number = models.CharField(max_length=100, unique=True, verbose_name="رقم العقد")
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

    second_party_name = models.CharField(max_length=255, verbose_name="اسم الطرف الثاني")
    building_name = models.CharField(max_length=255, verbose_name="اسم المبنى")
    activity = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="النشاط"
    )
    building_location = models.TextField(blank=True, null=True, verbose_name="موقع المبنى")
    client_identifier = models.CharField(max_length=100, blank=True, null=True, verbose_name="معرف العميل")

    start_date = models.DateField(verbose_name="تاريخ البداية")
    end_date = models.DateField(verbose_name="تاريخ النهاية")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "عقد صيانة"
        verbose_name_plural = "عقود الصيانة"

    def __str__(self):
        return f"{self.contract_number} - {self.second_party_name}"


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