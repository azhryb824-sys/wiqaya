from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0004_contract_client_decision_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancecontract",
            name="google_maps_url",
            field=models.URLField(
                blank=True,
                null=True,
                verbose_name="رابط موقع المبنى في خرائط جوجل"
            ),
        ),
        migrations.AddField(
            model_name="maintenancecontract",
            name="latitude",
            field=models.FloatField(
                blank=True,
                null=True,
                verbose_name="خط العرض"
            ),
        ),
        migrations.AddField(
            model_name="maintenancecontract",
            name="longitude",
            field=models.FloatField(
                blank=True,
                null=True,
                verbose_name="خط الطول"
            ),
        ),
    ]
