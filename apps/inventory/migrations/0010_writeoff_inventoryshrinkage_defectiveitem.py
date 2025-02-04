# Generated by Django 4.2.16 on 2025-01-06 13:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0009_remove_inventoryshrinkage_inventory_item_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='WriteOff',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('reason', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('inventory_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='write_offs', to='inventory.inventory')),
            ],
        ),
        migrations.CreateModel(
            name='InventoryShrinkage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('date_discovered', models.DateTimeField()),
                ('reason', models.CharField(choices=[('theft', 'Theft'), ('damage', 'Damage'), ('miscount', 'Miscount'), ('other', 'Other')], max_length=255)),
                ('additional_details', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('inventory_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shrinkages', to='inventory.inventory')),
                ('recorded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='DefectiveItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField()),
                ('defect_description', models.TextField()),
                ('action_taken', models.CharField(choices=[('return_to_supplier', 'Return to Supplier'), ('write_off', 'Write Off'), ('repair', 'Repair')], default='write_off', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('inventory_item', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='defective_items', to='inventory.inventory')),
            ],
        ),
    ]
