# Generated by Django 5.1.2 on 2024-12-03 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farminsight_dashboard_backend', '0011_alter_image_camera_alter_image_image_delete_snapshot'),
    ]

    operations = [
        migrations.AlterField(
            model_name='growingcycle',
            name='endDate',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='growingcycle',
            name='note',
            field=models.CharField(blank=True, max_length=256),
        ),
    ]
