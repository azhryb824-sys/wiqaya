from django.urls import path
from . import views

# 🔥 مهم جداً
app_name = "certificates"

urlpatterns = [
    # -----------------------------
    # الشهادات
    # -----------------------------
    path("", views.certificate_list_view, name="certificate_list"),
    path("create/", views.certificate_create_view, name="certificate_create"),
    path(
        "create/from-contract/<int:contract_id>/",
        views.certificate_create_view,
        name="certificate_create_from_contract"
    ),

    path("<int:certificate_id>/", views.certificate_detail_view, name="certificate_detail"),
    path("<int:certificate_id>/print/", views.certificate_print_view, name="certificate_print"),

    # تنزيل PDF
    path("<int:certificate_id>/download/", views.certificate_download_pdf_view, name="certificate_download"),

    # -----------------------------
    # قوالب البنود
    # -----------------------------
    path("clauses/", views.certificate_clause_template_list_view, name="certificate_clause_list"),
    path("clauses/create/", views.certificate_clause_template_create_view, name="certificate_clause_create"),
]
