# Generated by Django 4.2.16 on 2025-05-27 12:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0009_paylaterdates"),
    ]

    operations = [
        migrations.AddField(
            model_name="paylaterdates",
            name="amount_paid",
            field=models.DecimalField(
                decimal_places=2, default=0, max_digits=10, null=True
            ),
        ),
    ]
