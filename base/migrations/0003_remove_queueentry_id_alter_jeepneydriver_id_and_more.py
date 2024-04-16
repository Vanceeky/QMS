# Generated by Django 4.2.5 on 2023-12-14 20:56

import base.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0002_alter_route_description_alter_station_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='queueentry',
            name='id',
        ),
        migrations.AlterField(
            model_name='jeepneydriver',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='queueentry',
            name='token_number',
            field=models.CharField(default=base.models.generate_short_id, editable=False, max_length=4, primary_key=True, serialize=False, unique=True),
        ),
    ]