# Generated by Django 5.2.1 on 2025-06-16 13:22

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0029_alter_accountbalance_negative_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="accountbalance",
            name="negative",
        ),
        migrations.RemoveField(
            model_name="accountbalance",
            name="negative_cost",
        ),
        migrations.RemoveField(
            model_name="accountbalance",
            name="positive",
        ),
        migrations.RemoveField(
            model_name="accountbalance",
            name="positive_cost",
        ),
    ]
