from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Core
    path("", include("core.urls")),

    # Apps (مهم جداً للـ namespace)
    path("contracts/", include(("contracts.urls", "contracts"), namespace="contracts")),
    path("certificates/", include(("certificates.urls", "certificates"), namespace="certificates")),
    path("visits/", include(("visits.urls", "visits"), namespace="visits")),
    path("quotations/", include(("quotations.urls", "quotations"), namespace="quotations")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
