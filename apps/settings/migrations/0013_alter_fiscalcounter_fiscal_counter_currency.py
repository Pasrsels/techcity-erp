# Generated by Django 4.2.16 on 2025-04-02 13:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0012_alter_fiscalcounter_fiscal_counter_currency_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="fiscalcounter",
            name="fiscal_counter_currency",
            field=models.CharField(
                choices=[("USD", "usd"), ("ZWL", "zwl")], default="USD", max_length=10
            ),
        ),
    ]
