# Generated by Django 4.2.16 on 2024-10-14 18:50

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0021_alter_invoice_note"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="invoice",
            name="due_date",
        ),
    ]