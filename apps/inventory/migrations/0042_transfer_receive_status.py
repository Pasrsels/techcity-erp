# Generated by Django 4.2.16 on 2024-10-31 18:26

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0041_transferitems_cost"),
    ]

    operations = [
        migrations.AddField(
            model_name="transfer",
            name="receive_status",
            field=models.BooleanField(default=False, null=True),
        ),
    ]