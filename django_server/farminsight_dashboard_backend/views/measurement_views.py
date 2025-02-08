from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import views, status
from rest_framework.response import Response
from farminsight_dashboard_backend.services import store_measurements_in_influx, valid_api_key_for_sensor


class MeasurementView(views.APIView):
    def post(self, request, sensor_id):
        """
        Store a single or a set of measurements for a given sensor in the InfluxDB
        at the fpf bucket
        :param request: HTTP request
        :param sensor_id: GUID of the sensor
        :return: HTTP response
        """
        if not 'Authorization' in request.headers:
            return Response(status=status.HTTP_403_FORBIDDEN)

        auth = request.headers['Authorization']
        if not auth.startswith('ApiKey'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        api_key = auth.split(' ')[1]
        if not (valid_api_key_for_sensor(api_key, sensor_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        store_measurements_in_influx(sensor_id, request.data)
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(
                f'sensor_updates_{sensor_id}', {"type": "sensor.measurement", "measurement": request.data}
            )
        return Response({"message": "Data written successfully"}, status=status.HTTP_201_CREATED)
