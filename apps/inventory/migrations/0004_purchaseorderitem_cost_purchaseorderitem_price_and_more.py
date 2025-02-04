# Generated by Django 4.2.16 on 2025-01-02 11:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_rename_receieved_quantity_transferitems_received_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorderitem',
            name='cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='purchaseorderitem',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='purchaseorderitem',
            name='wholesale_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ]
