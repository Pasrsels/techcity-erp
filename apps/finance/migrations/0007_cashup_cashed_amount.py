# Generated by Django 5.2.1 on 2025-05-24 14:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0006_alter_cashbook_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name="cashup",
            name="cashed_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
