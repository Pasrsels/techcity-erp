# Generated by Django 4.2.16 on 2025-02-17 08:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0009_remove_cashflow_expense_category_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="cashflow",
            name="expense_category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="finance.mainexpensecategory",
            ),
        ),
        migrations.AddField(
            model_name="cashflow",
            name="income_category",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="finance.mainincomecategory",
            ),
        ),
    ]
