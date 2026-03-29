from django.urls import path
from . import views

urlpatterns = [
    path("", views.visit_list_view, name="visit_list"),
    path("create/", views.visit_create_view, name="visit_create"),
    path("<int:visit_id>/", views.visit_detail_view, name="visit_detail"),
    path("<int:visit_id>/print/", views.visit_print_view, name="visit_print"),
    path("<int:visit_id>/add-note/", views.visit_add_note_view, name="visit_add_note"),

    path("<int:visit_id>/sign-technician/", views.visit_sign_technician_view, name="visit_sign_technician"),

    path("<int:visit_id>/technician-approve/", views.visit_technician_approve_view, name="visit_technician_approve"),
    path("<int:visit_id>/client-approve/", views.visit_client_approve_view, name="visit_client_approve"),

    path("contract/<int:contract_id>/log/", views.contract_visits_log_view, name="contract_visits_log"),
    path("contract/<int:contract_id>/log/print/", views.contract_visits_log_print_view, name="contract_visits_log_print"),
]