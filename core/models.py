from django.contrib.auth.models import AbstractUser
from django.db import models

import random
from datetime import timedelta
from django.utils import timezone


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

    national_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="رقم الهوية / السجل",
    )

    must_change_password = models.BooleanField(
        default=False,
        verbose_name="يجب تغيير كلمة المرور",
    )

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def __str__(self):
        full_name = self.get_full_name().strip()
        return full_name if full_name else self.username

    # 🔥 تنظيف رقم الجوال تلقائياً
    def get_clean_phone(self):
        if not self.phone:
            return ""

        phone = "".join(ch for ch in self.phone if ch.isdigit())

        # تحويل 05 → 9665
        if phone.startswith("05"):
            phone = "966" + phone[1:]

        # إزالة + لو موجود
        if phone.startswith("+"):
            phone = phone[1:]

        return phone


# =========================
# المؤسسة
# =========================
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


# =========================
# OTP تسجيل الدخول 🔐
# =========================
class LoginOTP(models.Model):
    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="login_otps",
        verbose_name="المستخدم",
    )

    code = models.CharField(
        max_length=6,
        verbose_name="رمز التحقق",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء",
    )

    is_used = models.BooleanField(
        default=False,
        verbose_name="تم الاستخدام",
    )

    class Meta:
        verbose_name = "رمز تحقق الدخول"
        verbose_name_plural = "رموز تحقق الدخول"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.user} - {self.code}"

    # ✅ صلاحية الكود (5 دقائق)
    def is_valid(self):
        return (
            not self.is_used
            and timezone.now() <= self.created_at + timedelta(minutes=5)
        )

    # 🔥 توليد كود
    @staticmethod
    def generate_code():
        return str(random.randint(100000, 999999))