# Generated by Django 5.1.2 on 2024-10-25 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farminsight_dashboard_backend', '0003_alter_userprofile_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fpf',
            name='cameraServiceIp',
            field=models.GenericIPAddressField(),
        ),
        migrations.AlterField(
            model_name='fpf',
            name='sensorServiceIp',
            field=models.GenericIPAddressField(),
        ),
    ]
