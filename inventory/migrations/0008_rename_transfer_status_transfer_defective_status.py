# Generated by Django 5.0.6 on 2024-06-30 22:33

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0007_transfer_quantity_transfer_transfer_status"),
    ]

    operations = [
        migrations.RenameField(
            model_name="transfer",
            old_name="transfer_status",
            new_name="defective_status",
        ),
    ]