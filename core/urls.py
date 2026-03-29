from django.urls import path, include
from . import views
from .views import CustomLoginView

urlpatterns = [
    # =========================
    # النظام العام
    # =========================
    path("", views.home_view, name="home"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("verify-login-otp/", views.verify_login_otp_view, name="verify_login_otp"),
    path("resend-login-otp/", views.resend_login_otp_view, name="resend_login_otp"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),

    # =========================
    # المؤسسة
    # =========================
    path("institution/create/", views.create_institution, name="create_institution"),
    path("institution/edit/", views.edit_my_institution, name="edit_my_institution"),

    # =========================
    # المستخدمين
    # =========================
    path("users/", views.users_list_view, name="users_list"),
    path("users/create/", views.create_user_view, name="create_user"),
    path("users/delete/<int:user_id>/", views.delete_user_view, name="delete_user"),

    # =========================
    # العقود
    # =========================
    path("contracts/", include("contracts.urls")),

    # =========================
    # الشهادات
    # =========================
    path("certificates/", include("certificates.urls")),

    # =========================
    # الزيارات
    # =========================
    path("visits/", include("visits.urls")),

    # =========================
    # عروض الأسعار
    # =========================
    path("quotations/", include("quotations.urls")),
]
