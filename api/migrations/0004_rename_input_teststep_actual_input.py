# Generated by Django 4.2.7 on 2025-06-24 11:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_rename_executed_on_testexecution_executed_device_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='teststep',
            old_name='input',
            new_name='actual_input',
        ),
    ]
