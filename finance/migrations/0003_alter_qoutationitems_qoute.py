# Generated by Django 5.0.6 on 2024-06-13 10:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0002_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="qoutationitems",
            name="qoute",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="qoute_items",
                to="finance.qoutation",
            ),
        ),
    ]