from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0003_contract_hijri_dates_and_duration"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancecontract",
            name="client_status",
            field=models.CharField(
                choices=[
                    ("pending", "بانتظار قرار العميل"),
                    ("approved", "موافق"),
                    ("rejected", "مرفوض"),
                    ("revision_requested", "طلب تعديل"),
                ],
                default="pending",
                max_length=30,
                verbose_name="قرار العميل",
            ),
        ),
        migrations.AddField(
            model_name="maintenancecontract",
            name="client_response_note",
            field=models.TextField(
                blank=True,
                null=True,
                verbose_name="ملاحظة العميل",
            ),
        ),
        migrations.AddField(
            model_name="maintenancecontract",
            name="client_response_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="تاريخ قرار العميل",
            ),
        ),
    ]
