# Generated by Django 4.2.16 on 2024-10-17 21:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0017_product_dealer_price"),
    ]

    operations = [
        migrations.CreateModel(
            name="costAllocationPurchaseOrder",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("allocated", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "allocationRate",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                ("expense_cost", models.DecimalField(decimal_places=2, max_digits=10)),
                ("price", models.DecimalField(decimal_places=2, max_digits=10)),
                ("quantity", models.IntegerField()),
                ("product", models.CharField(max_length=255)),
                ("total", models.DecimalField(decimal_places=2, max_digits=10)),
                ("total_buying", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "purchase_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="inventory.purchaseorder",
                    ),
                ),
            ],
        ),
    ]