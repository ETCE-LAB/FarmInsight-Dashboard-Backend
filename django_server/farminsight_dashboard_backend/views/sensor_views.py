from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from farminsight_dashboard_backend.serializers import SensorSerializer
from farminsight_dashboard_backend.services import is_member, get_organization_by_sensor_id, \
    get_organization_by_fpf_id, get_sensor_hardware_configuration, get_sensor_types, is_admin, set_sensor_order
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

        fpf_sensor_info = get_sensor_hardware_configuration(sensor)
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

        serializer = create_sensor(fpf_id, request.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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

        serializer = update_sensor(sensor_id, request.data)

        logger.info('Sensor updated successfully', extra={'resource_id': sensor_id})

        return Response(serializer.data, status=status.HTTP_200_OK)


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

    sensor_types = get_sensor_types(fpf_id)
    return Response(sensor_types, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_sensor_order(request, fpf_id):
    if not is_admin(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = set_sensor_order(request.data)

    return Response(data=serializer.data, status=status.HTTP_200_OK)
