from django.urls import path
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
]
