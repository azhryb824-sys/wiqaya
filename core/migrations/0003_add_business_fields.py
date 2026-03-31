from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_alter_user_phone_loginotp"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="business_name",
            field=models.CharField(
                max_length=255,
                blank=True,
                null=True,
                verbose_name="اسم المنشأة",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="business_unified_number",
            field=models.CharField(
                max_length=100,
                blank=True,
                null=True,
                verbose_name="الرقم الموحد للمنشأة",
            ),
        ),
    ]
