# Generated by Django 5.0.6 on 2024-07-16 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0013_customerdeposits_cashier_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerdeposits',
            name='payment_reference',
            field=models.CharField(default='cash-ref', max_length=255, unique=True),
        ),
    ]