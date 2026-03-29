from django.contrib import admin
from .models import (
    CompletionCertificate,
    CompletionCertificateClause,
    CertificateClauseTemplate,
)

admin.site.register(CompletionCertificate)
admin.site.register(CompletionCertificateClause)
admin.site.register(CertificateClauseTemplate)