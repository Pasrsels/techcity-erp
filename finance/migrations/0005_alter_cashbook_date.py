# Generated by Django 5.0.6 on 2024-06-13 11:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0004_alter_cashbook_date"),
    ]

    operations = [
        migrations.AlterField(
            model_name="cashbook",
            name="date",
            field=models.DateField(auto_now_add=True),
        ),
    ]