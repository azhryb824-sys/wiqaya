from django.contrib import admin
from .models import MaintenanceContract, MaintenanceContractClause, ContractClauseTemplate

admin.site.register(MaintenanceContract)
admin.site.register(MaintenanceContractClause)
admin.site.register(ContractClauseTemplate)