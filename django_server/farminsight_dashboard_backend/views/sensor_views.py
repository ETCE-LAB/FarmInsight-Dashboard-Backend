import uuid

from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from farminsight_dashboard_backend.serializers import SensorSerializer, SensorDBSchemaSerializer
from farminsight_dashboard_backend.services import is_member, send_request_to_fpf, get_organization_by_sensor_id, get_organization_by_fpf_id
from farminsight_dashboard_backend.services.sensor_services import get_sensor, create_sensor, update_sensor
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


class SensorView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sensor_id):
        """
        Return the sensor by its id.
        Requesting user must be part of the organization.
        :param request:
        :param sensor_id:
        :return:
        """
        if not is_member(request.user, get_organization_by_sensor_id(sensor_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        sensor = get_sensor(sensor_id)

        fpf_sensor_info = send_request_to_fpf(sensor.FPF_id, 'get', f'/api/sensors/{sensor_id}')
        # todo returns here interval, wich will be duplicated information in the response
        sensor_data = SensorSerializer(sensor).data

        return Response({**sensor_data, "hardwareConfiguration": fpf_sensor_info}, status=status.HTTP_200_OK)

    def post(self, request):
        """
        Generate a new uuid for the sensor.
        Forward required sensor information to the FPF with the newly created sensor id.
        If successful, create the sensor in the database.
        Requesting user must be a member of the organization.
        :param request:
        :return:
        """
        fpf_id = request.data.get('fpfId')

        if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        sensor = request.data

        # Generate a new UUID for the sensor
        new_uuid = uuid.uuid4()

        # Build new sensor object
        sensor["id"] = str(new_uuid)
        sensor['FPF'] = fpf_id

        # Validate the sensor object before sending it to the FPF
        serializer = SensorDBSchemaSerializer(data=sensor, partial=True)
        serializer.is_valid(raise_exception=True)

        fpf_sensor_config = {
            "id": sensor.get('id'),
            "intervalSeconds": sensor.get('intervalSeconds'),
            "sensorClassId": sensor.get('hardwareConfiguration').get('sensorClassId', ''),
            "additionalInformation": sensor.get('hardwareConfiguration').get('additionalInformation', {}),
            "isActive": sensor.get('isActive'),
        }

        try:
            send_request_to_fpf(fpf_id, 'post', '/api/sensors', fpf_sensor_config)

        except Exception as e:
            raise Exception(f"Unable to create sensor at FPF. {e}")

        return Response(create_sensor(sensor), status=status.HTTP_200_OK)

    def put(self, request, sensor_id):
        """
        Update the sensor by its id
        The requesting user must be part of the organization.
        If technical details like interval or connection type changed, sync with fpf
        If this is successful, update the local database and return OK.
        Requesting user must be a member of the organization.
        :param sensor_id:
        :param request:
        :return:
        """
        if not is_member(request.user, get_organization_by_sensor_id(sensor_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        data = request.data
        fpf_id = get_sensor(sensor_id).FPF_id

        # Update sensor on FPF
        update_fpf_payload = {
            "intervalSeconds": data.get('intervalSeconds'),
            "sensorClassId": data.get('hardwareConfiguration', {}).get('sensorClassId', ''),
            "additionalInformation": data.get('hardwareConfiguration', {}).get('additionalInformation', {}),
            "isActive": data.get('isActive'),
        }

        send_request_to_fpf(fpf_id, 'put', f'/api/sensors/{sensor_id}', update_fpf_payload)

        # Update sensor locally
        update_sensor_payload = {key: value for key, value in data.items() if key != "connection"}
        update_sensor(sensor_id, update_sensor_payload)

        logger.info('sensor updated successfully', extra={'resource_id': sensor_id})

        return Response(data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fpf_sensor_types(request, fpf_id):
    """
    Verify that the fpf exists
    try to send a request to the fpf
    :return:
    """
    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    sensor_types = send_request_to_fpf(fpf_id, 'get', '/api/sensors/types')
    return Response(sensor_types, status=status.HTTP_200_OK)
