# Generated by Django 5.2.1 on 2025-06-16 09:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0013_stocktakeitem_cost"),
    ]

    operations = [
        migrations.AddField(
            model_name="stocktakeitem",
            name="note",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
    ]
