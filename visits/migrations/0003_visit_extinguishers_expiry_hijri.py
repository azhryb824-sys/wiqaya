from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("visits", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="visit",
            name="extinguishers_expiry_hijri",
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                verbose_name="تاريخ انتهاء الطفايات (هجري)",
                help_text="مثال: 15 شوال 1447هـ",
            ),
        ),
    ]
