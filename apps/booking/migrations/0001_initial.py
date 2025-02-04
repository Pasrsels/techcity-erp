# Generated by Django 4.2.16 on 2024-12-12 09:33

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='itemOfUseName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('item_of_use_name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='MemberAccounts',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Balance', models.DecimalField(decimal_places=2, default=0.0, max_digits=8)),
                ('delete', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Payments',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Date', models.CharField(default=django.utils.timezone.now)),
                ('Amount', models.DecimalField(decimal_places=2, default=0.0, max_digits=8)),
                ('Admin_fee', models.DecimalField(decimal_places=2, default=0.0, max_digits=8)),
                ('Description', models.CharField(default='', max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='ServiceRange',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_range', models.CharField(default='none', max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='UnitMeasurement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('measurement', models.CharField(max_length=60, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Services',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_name', models.CharField(default='', max_length=255)),
                ('description', models.CharField(default='none', max_length=255)),
                ('service_range', models.CharField(default='none', max_length=255)),
                ('unit_measure', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='booking.unitmeasurement')),
            ],
        ),
        migrations.CreateModel(
            name='Members',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('National_ID', models.CharField(max_length=15)),
                ('Name', models.CharField(max_length=50)),
                ('Email', models.EmailField(max_length=255)),
                ('Phone', models.CharField(max_length=12)),
                ('Address', models.CharField(max_length=255)),
                ('Company', models.CharField(blank=True, max_length=255)),
                ('Age', models.IntegerField()),
                ('delete', models.BooleanField(default=False)),
                ('Member_accounts', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='booking.memberaccounts')),
                ('Payments', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='booking.payments')),
                ('Services', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='booking.services')),
            ],
        ),
        migrations.AddField(
            model_name='memberaccounts',
            name='Payments',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.payments'),
        ),
        migrations.CreateModel(
            name='Logs',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', 'create'), ('update', 'update'), ('read', 'read'), ('delete', 'delete')], max_length=10)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('Members', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.members')),
                ('Payments', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.payments')),
                ('Services', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs_file', to='booking.services')),
            ],
        ),
        migrations.CreateModel(
            name='ItemOfUse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=0)),
                ('cost', models.DecimalField(decimal_places=2, default=0.0, max_digits=4)),
                ('description', models.CharField(default='none', max_length=255, null=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.category')),
                ('name', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.itemofusename')),
                ('service', models.ManyToManyField(to='booking.services')),
            ],
        ),
        migrations.CreateModel(
            name='inventory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('cost', models.DecimalField(decimal_places=2, default=0.0, max_digits=5)),
                ('quantity', models.IntegerField(default=0)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.category')),
            ],
        ),
    ]
