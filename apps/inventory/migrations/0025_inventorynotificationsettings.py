# Generated by Django 4.2.16 on 2025-06-26 13:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inventory", "0024_stocktakeitem_now_quantity"),
    ]

    operations = [
        migrations.CreateModel(
            name="InventoryNotificationSettings",
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
                ("low_stock", models.BooleanField(default=True)),
                ("out_of_stock", models.BooleanField(default=True)),
                ("movement_create", models.BooleanField(default=True)),
                ("movement_update", models.BooleanField(default=True)),
                ("movement_delete", models.BooleanField(default=True)),
                ("movement_transfer", models.BooleanField(default=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
