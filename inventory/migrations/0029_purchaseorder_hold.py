# Generated by Django 4.2.16 on 2024-10-22 12:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0028_purchaseorderitem_dealer_expected_profit"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorder",
            name="hold",
            field=models.BooleanField(default=True, null=True),
        ),
    ]