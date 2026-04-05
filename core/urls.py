from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .views import CustomLoginView

urlpatterns = [
    # =========================
    # النظام العام
    # =========================
    path("", views.home_view, name="home"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),

    # =========================
    # الصفحات العامة
    # =========================
    path("terms/", views.terms_view, name="terms"),
    path("subscription-terms/", views.subscription_terms_view, name="subscription_terms"),

    # =========================
    # استعادة كلمة المرور
    # =========================
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset.html"
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="registration/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="registration/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

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
