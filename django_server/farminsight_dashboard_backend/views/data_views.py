from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from django_server import settings
from farminsight_dashboard_backend.serializers import DateRangeSerializer, FPFFullDataSerializer, ImageURLSerializer
from farminsight_dashboard_backend.services import get_all_fpf_data, get_all_sensor_data, get_images_by_camera


@api_view(['GET'])
def get_fpf_data(request, fpf_id):
    """
    Get all data for the given FPF including all sensor measurements
    and all images
    :param fpf_id: UUID of the FPF
    :param request:
    Query param: from must be in ISO 8601 format (e.g. 2024-10-01T00:00:00Z) or simpler YYYY-MM-DD format.
    Query param: to  must be in ISO 8601 format (e.g. 2024-10-31T23:59:59Z) or simpler YYYY-MM-DD format.
    :return: http response with fpf information as json
    """
    serializer = DateRangeSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    from_date = serializer.validated_data.get('from_date')
    to_date = serializer.validated_data.get('to_date')

    serializer = FPFFullDataSerializer(get_all_fpf_data(fpf_id), context={'from_date': from_date,
                                                                          'to_date': to_date,
                                                                          'request': request})

    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_sensor_data(request, sensor_id):
    """
    Get all measurements for a given sensor
    :param sensor_id:
    :param request:
    :return: http response with measurement information as json
    """
    serializer = DateRangeSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    from_date = serializer.validated_data.get('from_date')
    to_date = serializer.validated_data.get('to_date')

    return Response(get_all_sensor_data(sensor_id, from_date, to_date))


@api_view(['GET'])
def get_camera_images(request, camera_id):
    """
    Get all images for a given camera in requested time range
    :param request:
    :param camera_id:
    :return:
    """
    serializer = DateRangeSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)

    from_date = serializer.validated_data.get('from_date')
    to_date = serializer.validated_data.get('to_date')

    images = get_images_by_camera(camera_id, from_date, to_date)

    return Response(ImageURLSerializer(images, many=True).data, status=200)