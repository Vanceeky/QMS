# Generated by Django 4.2.5 on 2023-12-14 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='route',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='station',
            name='description',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
