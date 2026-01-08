# Generated manually to add missing rMMForecastName field to Threshold

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farminsight_dashboard_backend', '0032_add_sensor_action_links_to_energy_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='threshold',
            name='rMMForecastName',
            field=models.CharField(blank=True, max_length=128, default=''),
            preserve_default=False,
        ),
    ]

