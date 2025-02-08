from rest_framework import serializers
from farminsight_dashboard_backend.models import Sensor
from farminsight_dashboard_backend.utils import get_date_range


class SensorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Sensor
        fields = [
            'id',
            'name',
            'location',
            'unit',
            'modelNr',
            'isActive',
            'intervalSeconds',
        ]


class SensorDataSerializer(serializers.ModelSerializer):
    measurements = serializers.SerializerMethodField()

    class Meta:
        model = Sensor
        fields = [
            'id',
            'name',
            'location',
            'unit',
            'modelNr',
            'isActive',
            'intervalSeconds',
            'measurements'
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

    class Meta:
        model = Sensor
        fields = [
            'id',
            'name',
            'location',
            'unit',
            'modelNr',
            'isActive',
            'intervalSeconds',
            'lastMeasurement'
        ]

    def get_lastMeasurement(self, obj):
        from farminsight_dashboard_backend.services import InfluxDBManager

        try:
            return InfluxDBManager.get_instance().fetch_latest_sensor_measurements(
                fpf_id=obj.FPF.id,
                sensor_ids=[str(obj.id)],
            ).get(str(obj.id), [])
        except Exception as e:
            return {'error': 'Could not fetch last measurement.'}

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
        fields = ['name']