from django.urls import path
from . import views

urlpatterns = [
    path("", views.contract_list_view, name="contracts_list"),
    path("create/", views.contract_create_view, name="contract_create"),
    path("<int:contract_id>/", views.contract_detail_view, name="contract_detail"),
    path("<int:contract_id>/edit/", views.contract_edit_view, name="contract_edit"),
    path("<int:contract_id>/print/", views.contract_print_view, name="contract_print),
    path("contracts/<int:contract_id>/download-pdf/", views.contract_download_pdf_view, name="contract_download_pdf"),
    path("<int:contract_id>/delete/", views.contract_delete_view, name="contract_delete"),

    path("<int:contract_id>/decision/", views.contract_client_decision_view, name="contract_client_decision"),

    path("clauses/", views.clause_template_list_view, name="clause_template_list"),
    path("clauses/create/", views.clause_template_create_view, name="clause_template_create"),
]
