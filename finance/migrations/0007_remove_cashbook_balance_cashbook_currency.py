# Generated by Django 5.0.6 on 2024-06-13 12:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0006_rename_date_cashbook_issue_date_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="cashbook",
            name="balance",
        ),
        migrations.AddField(
            model_name="cashbook",
            name="currency",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                to="finance.currency",
            ),
            preserve_default=False,
        ),
    ]