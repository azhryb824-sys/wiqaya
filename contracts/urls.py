from django.urls import path
from . import views

# 🔥 تعريف اسم التطبيق (مهم لمنع تعارض namespaces)
app_name = "contracts"

urlpatterns = [
    # -----------------------------
    # العقود
    # -----------------------------
    path("", views.contract_list_view, name="contracts_list"),
    path("create/", views.contract_create_view, name="contract_create"),
    path("<int:contract_id>/", views.contract_detail_view, name="contract_detail"),
    path("<int:contract_id>/edit/", views.contract_edit_view, name="contract_edit"),

    # طباعة
    path("<int:contract_id>/print/", views.contract_print_view, name="contract_print"),

    # تنزيل PDF
    path("<int:contract_id>/download/", views.contract_download_pdf_view, name="contract_download"),

    # حذف
    path("<int:contract_id>/delete/", views.contract_delete_view, name="contract_delete"),

    # قرار العميل
    path("<int:contract_id>/decision/", views.contract_client_decision_view, name="contract_client_decision"),

    # -----------------------------
    # قوالب البنود
    # -----------------------------
    path("clauses/", views.clause_template_list_view, name="clause_template_list"),
    path("clauses/create/", views.clause_template_create_view, name="clause_template_create"),
]
