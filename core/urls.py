from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("terms/", views.terms_view, name="terms"),
    path("subscription-terms/", views.subscription_terms_view, name="subscription_terms"),
    path("subscriptions/", views.subscriptions_view, name="subscriptions"),

    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.client_profile_view, name="client_profile"),

    path("institution/create/", views.create_institution, name="create_institution"),
    path("institution/edit/", views.edit_my_institution, name="edit_my_institution"),

    path("users/", views.users_list_view, name="users_list"),
    path("users/create/", views.create_user_view, name="create_user"),
    path("users/<int:user_id>/", views.user_detail_view, name="user_detail"),
    path("users/<int:user_id>/delete/", views.delete_user_view, name="delete_user"),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="core/password_reset.html",
            email_template_name="core/password_reset_email.html",
            subject_template_name="core/password_reset_subject.txt",
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="core/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="core/password_reset_confirm.html",
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="core/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
]
