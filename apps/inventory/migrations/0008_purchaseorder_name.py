# Generated by Django 4.2.16 on 2025-06-11 12:35

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0007_temporarypurchaseorder_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaseorder",
            name="name",
            field=models.CharField(default="", max_length=255, null=True),
        ),
    ]
