# Generated by Django 4.2.23 on 2025-06-18 04:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='clients_plan_id',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='platform_plan_id',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='professional_plan_id',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
    ]
