from rest_framework import views, status
from rest_framework.response import Response
from .models import Sensor
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from django.conf import settings


class MeasurementView(views.APIView):
    def post(self, request, sensorId):
        """
        Store a single or a set of measurements for a given sensor in the InfluxDB
        at the fpf bucket
        :param request: HTTP request
        :param sensorId: GUID of the sensor
        :return: HTTP response
        """
        data = request.data
        sensor = Sensor.objects.get(id=sensorId)

        influxdb_settings = getattr(settings, 'INFLUXDB_CLIENT_SETTINGS', {})

        client = InfluxDBClient(url=influxdb_settings['url'],
                                token=influxdb_settings['token'],
                                org=influxdb_settings['org'])

        write_api = client.write_api(write_options=SYNCHRONOUS)

        points = []
        for measurement in data:
            point = (
                Point("SensorData")
                .tag("sensorId", str(sensorId))
                .field("value", float(measurement['value']))
                .time(measurement['measuredAt'], WritePrecision.NS)
            )
            points.append(point)

        write_api.write(bucket=str(sensor.FPF_id), record=points)
        client.close()

        return Response({"message": "Data written successfully"}, status=status.HTTP_201_CREATED)
