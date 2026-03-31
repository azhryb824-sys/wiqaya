from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    USER_TYPES = (
        ("executive", "مدير تنفيذي"),
        ("admin_assistant", "مساعد إداري"),
        ("technician", "فني"),
        ("client", "عميل"),
    )

    user_type = models.CharField(
        max_length=30,
        choices=USER_TYPES,
        default="client",
        verbose_name="نوع المستخدم",
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="رقم الجوال",
        help_text="مثال: 9665XXXXXXXX",
    )

    # ✅ رقم الهوية (فريد)
    national_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        verbose_name="رقم الهوية / السجل",
    )

    # ✅ اسم المنشأة
    business_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="اسم المنشأة",
    )

    # ✅ الرقم الموحد (فريد)
    business_unified_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        verbose_name="الرقم الموحد للمنشأة",
    )

    must_change_password = models.BooleanField(
        default=False,
        verbose_name="يجب تغيير كلمة المرور",
    )

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def __str__(self):
        return self.get_display_name()

    # =========================
    # 📱 تنظيف رقم الجوال
    # =========================
    def get_clean_phone(self):
        if not self.phone:
            return ""

        phone = "".join(ch for ch in self.phone if ch.isdigit())

        if phone.startswith("05"):
            phone = "966" + phone[1:]

        if phone.startswith("5") and len(phone) == 9:
            phone = "966" + phone

        return phone

    # =========================
    # 👤 اسم العرض
    # =========================
    def get_display_name(self):
        full_name = self.get_full_name().strip()
        return full_name if full_name else self.username

    # =========================
    # 🏢 هل هذا الرقم هو رقم منشأة؟
    # =========================
    def is_business_identifier(self, identifier):
        identifier = (identifier or "").strip()
        return self.business_unified_number and identifier == self.business_unified_number

    # =========================
    # 🔥 تحديد اسم الطرف الثاني
    # =========================
    def get_second_party_name_by_identifier(self, identifier):
        identifier = (identifier or "").strip()

        # إذا كان الرقم الموحد → اسم المنشأة
        if self.is_business_identifier(identifier):
            return self.business_name or self.get_display_name()

        # غير ذلك → اسم العميل
        return self.get_display_name()

    # =========================
    # 🔍 هل الرقم يطابق المستخدم؟
    # =========================
    def matches_identifier(self, identifier):
        identifier = (identifier or "").strip()

        return (
            (self.national_id and identifier == self.national_id)
            or
            (self.business_unified_number and identifier == self.business_unified_number)
        )


class Institution(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="اسم المؤسسة",
    )

    unified_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="الرقم الموحد",
    )

    executive_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="اسم المدير التنفيذي",
    )

    logo = models.ImageField(
        upload_to="institution/logos/",
        blank=True,
        null=True,
        verbose_name="الشعار",
    )

    letterhead = models.ImageField(
        upload_to="institution/letterheads/",
        blank=True,
        null=True,
        verbose_name="مطبوعات المؤسسة",
    )

    stamp = models.ImageField(
        upload_to="institution/stamps/",
        blank=True,
        null=True,
        verbose_name="الختم",
    )

    signature = models.ImageField(
        upload_to="institution/signatures/",
        blank=True,
        null=True,
        verbose_name="التوقيع",
    )

    users = models.ManyToManyField(
        "User",
        related_name="institutions",
        blank=True,
        verbose_name="المستخدمون",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء",
    )

    class Meta:
        verbose_name = "مؤسسة"
        verbose_name_plural = "المؤسسات"

    def __str__(self):
        return self.name
