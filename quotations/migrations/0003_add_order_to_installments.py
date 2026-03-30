from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quotations", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricequotationinstallment",
            name="order",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="الترتيب",
            ),
        ),
    ]
