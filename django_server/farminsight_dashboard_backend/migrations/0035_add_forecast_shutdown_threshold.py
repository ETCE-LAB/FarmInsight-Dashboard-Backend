# Generated migration for forecast shutdown threshold fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('farminsight_dashboard_backend', '0034_add_model_type_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='energyconsumer',
            name='forecastShutdownThreshold',
            field=models.IntegerField(
                default=0,
                help_text='Predicted battery percentage at which to schedule shutdown (0 = disabled). When AI model predicts battery will reach this level, the consumer will be shut down.'
            ),
        ),
        migrations.AddField(
            model_name='energyconsumer',
            name='forecastBufferDays',
            field=models.IntegerField(
                default=0,
                help_text='Number of days before predicted threshold to execute shutdown (0 = shutdown exactly when predicted level is reached)'
            ),
        ),
    ]
