import dateutil.parser
from django.utils import timezone

from rest_framework import serializers
from farminsight_dashboard_backend.models import Sensor
from farminsight_dashboard_backend.utils import get_date_range
from .threshold_serializer import ThresholdSerializer


class SensorSerializer(serializers.ModelSerializer):
    thresholds = ThresholdSerializer(many=True)

    class Meta:
        model = Sensor
        fields = [
            'id',
            'name',
            'location',
            'unit',
            'parameter',
            'modelNr',
            'isActive',
            'intervalSeconds',
            'thresholds',
        ]


class SensorDataSerializer(serializers.ModelSerializer):
    measurements = serializers.SerializerMethodField()
    thresholds = ThresholdSerializer(many=True)

    class Meta:
        model = Sensor
        fields = [
            'id',
            'name',
            'location',
            'unit',
            'parameter',
            'modelNr',
            'isActive',
            'intervalSeconds',
            'measurements',
            'thresholds',
        ]

    def get_measurements(self, obj):
        from farminsight_dashboard_backend.services import InfluxDBManager

        from_date = self.context.get('from_date')
        to_date = self.context.get('to_date')
        from_date_iso, to_date_iso = get_date_range(from_date, to_date)

        return InfluxDBManager.get_instance().fetch_sensor_measurements(
            fpf_id=obj.FPF.id,
            sensor_ids=[str(obj.id)],
            from_date=from_date_iso,
            to_date=to_date_iso,
        ).get(str(obj.id), [])


class SensorLastValueSerializer(serializers.ModelSerializer):
    lastMeasurement = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    thresholds = ThresholdSerializer(many=True)

    class Meta:
        model = Sensor
        fields = [
            'id',
            'name',
            'location',
            'unit',
            'parameter',
            'modelNr',
            'isActive',
            'intervalSeconds',
            'lastMeasurement',
            'status',
            'thresholds',
        ]

    def get_lastMeasurement(self, obj):
        from farminsight_dashboard_backend.services import InfluxDBManager

        try:
            value = InfluxDBManager.get_instance().fetch_latest_sensor_measurements(
                fpf_id=obj.FPF.id,
                sensor_ids=[str(obj.id)],
            ).get(str(obj.id), [])
            self.measured_at = value['measuredAt']
            return value
        except Exception as e:
            self.measured_at = None
            return {'error': 'Could not fetch last measurement.'}

    def get_status(self, obj):
        if not obj.isActive:
            return 'grey'

        if self.measured_at is not None:
            seconds_since_last_measurement = (timezone.now() - dateutil.parser.isoparse(self.measured_at)).total_seconds()
            if seconds_since_last_measurement < obj.intervalSeconds:
                return 'green'
            elif seconds_since_last_measurement < 2 * obj.intervalSeconds:
                return 'yellow'

        return 'red'


class SensorDBSchemaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = '__all__'
        extra_kwargs = {
            'additional_fields': {'required': False}
        }


class PreviewSensorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sensor
        fields = ['name', 'parameter']