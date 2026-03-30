from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quotations", "0003_add_order_to_installments"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricequotation",
            name="transfer_receipt",
            field=models.ImageField(
                upload_to="quotation_transfer_receipts/",
                blank=True,
                null=True,
                verbose_name="إيصال التحويل",
            ),
        ),
        migrations.AddField(
            model_name="pricequotation",
            name="payment_proof_uploaded_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="تاريخ رفع إيصال التحويل",
            ),
        ),
    ]
