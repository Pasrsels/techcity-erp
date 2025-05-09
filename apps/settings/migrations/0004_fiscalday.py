# Generated by Django 4.2.16 on 2025-03-17 14:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("settings", "0003_offlinereceipt"),
    ]

    operations = [
        migrations.CreateModel(
            name="FiscalDay",
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
                ("day_no", models.IntegerField(default=1)),
                ("is_open", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
