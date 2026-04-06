from datetime import date

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from hijridate import Gregorian

from contracts.models import MaintenanceContract
from visits.models import Visit

from .forms import (
    ArabicLoginForm,
    ClientProfileForm,
    CreateUserForm,
    InstitutionForm,
    RegisterForm,
)
from .models import User


# =========================
# الصفحات العامة
# =========================
def subscription_terms_view(request):
    return render(request, "core/subscription_terms.html")


def terms_view(request):
    return render(request, "core/terms.html")


# ✅ تمت الإضافة هنا
def subscriptions_view(request):
    return render(request, "core/subscriptions.html")


# =========================
# تحويل التاريخ الهجري
# =========================
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


def get_hijri_parts(gregorian_date):
    hijri = Gregorian(
        gregorian_date.year,
        gregorian_date.month,
        gregorian_date.day
    ).to_hijri()
    return hijri.year, hijri.month, hijri.day


def format_hijri_date(gregorian_date):
    if not gregorian_date:
        return "-"
    h_year, h_month, h_day = get_hijri_parts(gregorian_date)
    month_name = ARABIC_HIJRI_MONTHS.get(h_month, str(h_month))
    return f"{h_day} {month_name} {h_year}هـ"


# =========================
# تسجيل الدخول
# =========================
class CustomLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = ArabicLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()

        if not user.is_active:
            messages.error(self.request, "هذا الحساب غير مفعل")
            return self.form_invalid(form)

        login(self.request, user)
        messages.success(self.request, "تم تسجيل الدخول بنجاح")
        return redirect("dashboard")

    def form_invalid(self, form):
        messages.error(self.request, "اسم المستخدم أو كلمة المرور غير صحيحة")
        return super().form_invalid(form)

    def get_success_url(self):
        return "/dashboard/"


# =========================
# الصفحة الرئيسية
# =========================
def home_view(request):
    return render(request, "core/home.html")


# =========================
# التسجيل
# =========================
def register_view(request):
    form = RegisterForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            user.is_active = True
            user.save(update_fields=["is_active"])
            messages.success(request, "تم إنشاء الحساب بنجاح")
            return redirect("login")

        print(form.errors)
        messages.error(request, "تعذر إنشاء الحساب")

    return render(request, "core/register.html", {"form": form})


# =========================
# الملف الشخصي
# =========================
@login_required
def client_profile_view(request):
    form = ClientProfileForm(request.POST or None, instance=request.user)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث البيانات")
            return redirect("client_profile")

        messages.error(request, "حدث خطأ")

    return render(request, "core/client_profile.html", {"form": form})


# =========================
# لوحة التحكم
# =========================
@login_required
def dashboard_view(request):
    stats = []
    institution = request.user.institutions.first()

    if request.user.user_type == "executive" and institution:
        stats = [
            {"title": "العقود", "value": MaintenanceContract.objects.filter(institution=institution).count()},
            {"title": "الزيارات", "value": Visit.objects.filter(contract__institution=institution).count()},
            {"title": "المستخدمون", "value": institution.users.count()},
        ]

    return render(request, "core/dashboard.html", {"stats": stats})


# =========================
# تسجيل الخروج
# =========================
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج")
    return redirect("home")


# =========================
# المؤسسة
# =========================
@login_required
def create_institution(request):
    form = InstitutionForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            institution = form.save()
            institution.users.add(request.user)
            messages.success(request, "تم إنشاء المؤسسة")
            return redirect("dashboard")

    return render(request, "core/institution_form.html", {"form": form})


@login_required
def edit_my_institution(request):
    institution = request.user.institutions.first()

    if not institution:
        return redirect("create_institution")

    form = InstitutionForm(request.POST or None, request.FILES or None, instance=institution)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "تم التعديل")
            return redirect("dashboard")

    return render(request, "core/institution_form.html", {"form": form})


# =========================
# المستخدمين
# =========================
@login_required
def users_list_view(request):
    institution = request.user.institutions.first()
    users = institution.users.all() if institution else []

    return render(request, "core/users_list.html", {"users": users})


@login_required
def user_detail_view(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)

    return render(
        request,
        "core/user_detail.html",
        {
            "user_obj": user_obj,
        },
    )


@login_required
def create_user_view(request):
    form = CreateUserForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            request.user.institutions.first().users.add(user)
            messages.success(request, "تم إنشاء المستخدم")
            return redirect("users_list")

    return render(request, "core/user_form.html", {"form": form})


@login_required
def delete_user_view(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "تم الحذف")
    return redirect("users_list")
