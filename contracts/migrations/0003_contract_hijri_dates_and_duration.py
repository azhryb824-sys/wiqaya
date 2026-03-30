from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contracts", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenancecontract",
            name="duration_years",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "عام"),
                    (2, "عامان"),
                    (3, "3 أعوام"),
                    (4, "4 أعوام"),
                    (5, "5 أعوام"),
                ],
                default=1,
                verbose_name="مدة العقد",
            ),
        ),
        migrations.AddField(
            model_name="maintenancecontract",
            name="start_date_hijri",
            field=models.CharField(
                max_length=50,
                blank=True,
                editable=False,
                verbose_name="تاريخ البداية هجري",
            ),
        ),
        migrations.AddField(
            model_name="maintenancecontract",
            name="end_date_hijri",
            field=models.CharField(
                max_length=50,
                blank=True,
                editable=False,
                verbose_name="تاريخ النهاية هجري",
            ),
        ),
        migrations.AlterField(
            model_name="maintenancecontract",
            name="end_date",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="تاريخ النهاية",
            ),
        ),
    ]
