# Generated by Django 4.2.7 on 2025-07-25 11:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='teststeptest',
            name='element_screenshots',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='teststeptest',
            name='input_field_type',
            field=models.CharField(blank=True, default='static', max_length=50, null=True),
        ),
    ]
