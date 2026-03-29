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

from .forms import ArabicLoginForm, CreateUserForm, InstitutionForm, RegisterForm
from .models import LoginOTP, User


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


def send_login_otp(user, code):
    # مؤقتاً يتم طباعة الرمز في التيرمنال
    # لاحقاً نستبدله بإرسال فعلي عبر واتساب
    print(f"LOGIN OTP for {user.username} / {user.phone}: {code}")


class CustomLoginView(LoginView):
    template_name = "core/login.html"
    authentication_form = ArabicLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        user = form.get_user()

        if not user.is_active:
            messages.error(self.request, "هذا الحساب غير مفعل")
            return self.form_invalid(form)

        # حذف أي رموز قديمة غير مستخدمة
        LoginOTP.objects.filter(user=user, is_used=False).delete()

        code = LoginOTP.generate_code()
        LoginOTP.objects.create(
            user=user,
            code=code,
        )

        send_login_otp(user, code)

        self.request.session["pending_otp_user_id"] = user.id
        self.request.session["pending_otp_username"] = user.username

        messages.success(self.request, "تم التحقق من كلمة المرور، أدخل رمز التحقق المرسل إليك")
        return redirect("verify_login_otp")

    def form_invalid(self, form):
        messages.error(self.request, "اسم المستخدم أو كلمة المرور غير صحيحة")
        return super().form_invalid(form)

    def get_success_url(self):
        return "/dashboard/"


def verify_login_otp_view(request):
    pending_user_id = request.session.get("pending_otp_user_id")

    if not pending_user_id:
        messages.error(request, "انتهت جلسة التحقق، سجل الدخول مرة أخرى")
        return redirect("login")

    user = get_object_or_404(User, id=pending_user_id)

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip()

        otp = LoginOTP.objects.filter(
            user=user,
            code=code,
            is_used=False,
        ).order_by("-id").first()

        if not otp or not otp.is_valid():
            messages.error(request, "رمز التحقق غير صحيح أو منتهي الصلاحية")
            return redirect("verify_login_otp")

        otp.is_used = True
        otp.save(update_fields=["is_used"])

        login(request, user)

        request.session.pop("pending_otp_user_id", None)
        request.session.pop("pending_otp_username", None)

        messages.success(request, "تم تسجيل الدخول بنجاح")
        return redirect("dashboard")

    return render(
        request,
        "core/verify_login_otp.html",
        {
            "pending_username": request.session.get("pending_otp_username", ""),
        },
    )


def resend_login_otp_view(request):
    pending_user_id = request.session.get("pending_otp_user_id")

    if not pending_user_id:
        messages.error(request, "انتهت جلسة التحقق، سجل الدخول مرة أخرى")
        return redirect("login")

    user = get_object_or_404(User, id=pending_user_id)

    LoginOTP.objects.filter(user=user, is_used=False).delete()

    code = LoginOTP.generate_code()
    LoginOTP.objects.create(
        user=user,
        code=code,
    )

    send_login_otp(user, code)

    messages.success(request, "تم إرسال رمز تحقق جديد")
    return redirect("verify_login_otp")


def home_view(request):
    return render(request, "core/home.html")


def register_view(request):
    form = RegisterForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            user.is_active = True
            user.save(update_fields=["is_active"])
            messages.success(request, "تم إنشاء الحساب بنجاح، يمكنك تسجيل الدخول الآن")
            return redirect("login")

        print(form.errors)
        messages.error(request, "تعذر إنشاء الحساب، راجع الأخطاء الظاهرة في النموذج")

    return render(request, "core/register.html", {"form": form})


@login_required
def dashboard_view(request):
    user_type_labels = {
        "executive": "المدير التنفيذي",
        "admin_assistant": "المساعد الإداري",
        "technician": "الفني",
        "client": "العميل",
    }

    stats = []
    executive_alerts = {
        "expiring_contracts": [],
        "contracts_without_visit": [],
        "pending_visits": [],
    }

    today = date.today()
    current_hijri_year, current_hijri_month, _ = get_hijri_parts(today)
    institution = request.user.institutions.first()

    if request.user.user_type == "executive":
        if not institution:
            stats = [{"title": "حساب جديد", "value": "1", "icon": "bi-person"}]
        else:
            contracts_count = MaintenanceContract.objects.filter(institution=institution).count()
            visits_count = Visit.objects.filter(contract__institution=institution).count()
            users_count = institution.users.count()

            expiring_contracts = []
            all_contracts = MaintenanceContract.objects.filter(institution=institution).order_by("end_date")

            for contract in all_contracts:
                if contract.end_date:
                    h_year, h_month, _ = get_hijri_parts(contract.end_date)
                    if h_year == current_hijri_year and h_month == current_hijri_month:
                        expiring_contracts.append(contract)

            executive_alerts["expiring_contracts"] = expiring_contracts

            active_contracts = MaintenanceContract.objects.filter(
                institution=institution,
                end_date__gte=today,
            )

            current_hijri_label = f"{ARABIC_HIJRI_MONTHS.get(current_hijri_month)} {current_hijri_year}هـ"
            contracts_without_visit = []

            for contract in active_contracts:
                has_visit_this_hijri_month = contract.visits.filter(
                    month_label=current_hijri_label
                ).exists()

                if not has_visit_this_hijri_month:
                    contracts_without_visit.append(contract)

            executive_alerts["contracts_without_visit"] = contracts_without_visit

            pending_visits = Visit.objects.filter(
                contract__institution=institution
            ).filter(
                Q(technician_approved=False) |
                Q(technician_approved=True, client_approved=False)
            ).order_by("-visit_date")

            executive_alerts["pending_visits"] = list(pending_visits)

            stats = [
                {"title": "العقود", "value": str(contracts_count), "icon": "bi-file-earmark-text"},
                {"title": "الزيارات", "value": str(visits_count), "icon": "bi-calendar2-check"},
                {"title": "المستخدمون", "value": str(users_count), "icon": "bi-people"},
            ]

    elif request.user.user_type == "admin_assistant":
        if not institution:
            stats = [{"title": "حساب جديد", "value": "1", "icon": "bi-person"}]
        else:
            stats = [
                {
                    "title": "العقود",
                    "value": str(MaintenanceContract.objects.filter(institution=institution).count()),
                    "icon": "bi-file-earmark-text",
                },
                {
                    "title": "الزيارات",
                    "value": str(Visit.objects.filter(contract__institution=institution).count()),
                    "icon": "bi-calendar2-check",
                },
                {
                    "title": "المستخدمون",
                    "value": str(institution.users.count()),
                    "icon": "bi-people",
                },
            ]

    elif request.user.user_type == "technician":
        stats = [
            {
                "title": "زياراتي",
                "value": str(Visit.objects.filter(technician=request.user).count()),
                "icon": "bi-tools",
            },
            {
                "title": "الزيارات المنجزة",
                "value": str(
                    Visit.objects.filter(
                        technician=request.user,
                        technician_approved=True,
                    ).count()
                ),
                "icon": "bi-check2-circle",
            },
            {
                "title": "الملاحظات",
                "value": str(
                    Visit.objects.filter(technician=request.user)
                    .exclude(notes__isnull=True)
                    .exclude(notes="")
                    .count()
                ),
                "icon": "bi-journal-text",
            },
        ]

    elif request.user.user_type == "client":
        stats = [
            {
                "title": "عقودي",
                "value": str(MaintenanceContract.objects.filter(client=request.user).count()),
                "icon": "bi-file-earmark-text",
            },
            {
                "title": "الزيارات",
                "value": str(Visit.objects.filter(contract__client=request.user).count()),
                "icon": "bi-calendar-event",
            },
            {
                "title": "الاعتمادات",
                "value": str(
                    Visit.objects.filter(
                        contract__client=request.user,
                        client_approved=True,
                    ).count()
                ),
                "icon": "bi-check2-square",
            },
        ]

    else:
        stats = [{"title": "الحساب", "value": "1", "icon": "bi-person"}]

    context = {
        "user_type_label": user_type_labels.get(request.user.user_type, "مستخدم"),
        "stats": stats,
        "executive_alerts": executive_alerts,
        "current_hijri_month_label": f"{ARABIC_HIJRI_MONTHS.get(current_hijri_month)} {current_hijri_year}هـ",
    }
    return render(request, "core/dashboard.html", context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "تم تسجيل الخروج بنجاح")
    return redirect("home")


@login_required
def create_institution(request):
    form = InstitutionForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            institution = form.save()
            institution.users.add(request.user)
            messages.success(request, "تم إنشاء المؤسسة")
            return redirect("dashboard")

        print(form.errors)
        messages.error(request, "تعذر إنشاء المؤسسة، راجع البيانات")

    return render(
        request,
        "core/institution_form.html",
        {
            "form": form,
            "page_title": "إنشاء مؤسسة",
        },
    )


@login_required
def edit_my_institution(request):
    institution = request.user.institutions.first()

    if not institution:
        messages.warning(request, "لا توجد مؤسسة مرتبطة بحسابك")
        return redirect("create_institution")

    form = InstitutionForm(request.POST or None, request.FILES or None, instance=institution)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "تم تحديث بيانات المؤسسة")
            return redirect("dashboard")

        print(form.errors)
        messages.error(request, "تعذر تحديث بيانات المؤسسة")

    return render(
        request,
        "core/institution_form.html",
        {
            "form": form,
            "page_title": "تعديل المؤسسة",
        },
    )


@login_required
def users_list_view(request):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = request.user.institutions.first()
    users = institution.users.all().order_by("-id") if institution else User.objects.none()

    return render(
        request,
        "core/users_list.html",
        {
            "users": users,
            "user_type_label": "إدارة المستخدمين",
        },
    )


@login_required
def create_user_view(request):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = request.user.institutions.first()
    if not institution:
        messages.error(request, "يجب إنشاء مؤسسة أولاً قبل إضافة مستخدمين")
        return redirect("create_institution")

    form = CreateUserForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            new_user = form.save()
            new_user.is_active = True
            new_user.save(update_fields=["is_active"])

            institution.users.add(new_user)

            messages.success(request, "تم إنشاء المستخدم بنجاح")
            return redirect("users_list")

        print(form.errors)
        messages.error(request, "تعذر إنشاء المستخدم، راجع الأخطاء الظاهرة في النموذج")

    return render(
        request,
        "core/user_form.html",
        {
            "form": form,
            "user_type_label": "إضافة مستخدم",
        },
    )


@login_required
def delete_user_view(request, user_id):
    if request.user.user_type not in ["executive", "admin_assistant"]:
        messages.error(request, "غير مصرح لك بالدخول لهذه الصفحة")
        return redirect("dashboard")

    institution = request.user.institutions.first()
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj == request.user:
        messages.error(request, "لا يمكنك حذف حسابك الحالي")
        return redirect("users_list")

    if institution and institution.users.filter(id=user_obj.id).exists():
        institution.users.remove(user_obj)

        if not user_obj.institutions.exists():
            user_obj.delete()

        messages.success(request, "تم حذف المستخدم بنجاح")
    else:
        messages.error(request, "هذا المستخدم غير تابع لمؤسستك")

    return redirect("users_list")