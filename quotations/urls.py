from django.urls import path
from . import views

# 🔥 مهم جداً عشان namespace
app_name = "quotations"

urlpatterns = [
    path("", views.quotation_list_view, name="quotation_list"),
    path("create/", views.quotation_create_view, name="quotation_create"),
    path("<int:quotation_id>/", views.quotation_detail_view, name="quotation_detail"),
    path("<int:quotation_id>/print/", views.quotation_print_view, name="quotation_print"),
    path("<int:quotation_id>/decision/", views.quotation_client_decision_view, name="quotation_client_decision"),
    path("<int:quotation_id>/payment-choice/", views.quotation_payment_choice_view, name="quotation_payment_choice"),
]
