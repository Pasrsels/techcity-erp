# Generated by Django 4.2.16 on 2024-10-19 11:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0021_purchaseorder_batch"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="product",
            name="batch_code",
        ),
        migrations.AddField(
            model_name="product",
            name="batch",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]