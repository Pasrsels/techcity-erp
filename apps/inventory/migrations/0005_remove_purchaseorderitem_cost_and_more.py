# Generated by Django 4.2.16 on 2025-01-02 11:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_purchaseorderitem_cost_purchaseorderitem_price_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='purchaseorderitem',
            name='cost',
        ),
        migrations.RemoveField(
            model_name='purchaseorderitem',
            name='price',
        ),
    ]
