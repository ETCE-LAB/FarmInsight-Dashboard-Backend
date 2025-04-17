from datetime import datetime

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from farminsight_dashboard_backend.serializers import DateRangeSerializer
from farminsight_dashboard_backend.services import valid_api_key_for_sensor, valid_api_key_for_fpf, write_log_message, \
    is_member, get_organization_by_fpf_id, get_organization_by_sensor_id, get_log_messages_by_date, \
    get_log_messages_by_amount, is_system_admin, get_organization_by_camera_id, get_organization_by_id


@api_view(['POST'])
def post_log_message(request):
    if not 'Authorization' in request.headers:
        return Response(status=status.HTTP_403_FORBIDDEN)

    auth = request.headers['Authorization']
    if not auth.startswith('ApiKey'):
        return Response(status=status.HTTP_403_FORBIDDEN)

    api_key = auth.split(' ')[1]

    related_resource_id = ''
    if 'sensorId' in request.data:
        related_resource_id = request.data['sensorId']
        if not valid_api_key_for_sensor(api_key, related_resource_id):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif 'fpfId' in request.data:
        related_resource_id = request.data['fpfId']
        if not valid_api_key_for_fpf(api_key, related_resource_id):
            return Response(status=status.HTTP_403_FORBIDDEN)

    created_at = datetime.fromisoformat(request.data['createdAt']) if 'createdAt' in request.data else None
    write_log_message(request.data['level'], request.data['message'], related_resource_id, created_at)
    return Response({"message": "Log written successfully"}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_log_messages(request, resource_type, resource_id):
    if resource_type == 'sensor':
        if not is_member(request.user, get_organization_by_sensor_id(resource_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif resource_type == 'camera':
        if not is_member(request.user, get_organization_by_camera_id(resource_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif resource_type == 'fpf':
        if not is_member(request.user, get_organization_by_fpf_id(resource_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif resource_type == 'org':
        if not is_member(request.user, get_organization_by_id(resource_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)
    elif resource_type == 'admin':
        if not is_system_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        return Response(status=status.HTTP_404_NOT_FOUND)

    # amount OR from_date query param is required, to_date is optional and defaults to now if from_date is used
    amount = int(request.GET.get('amount', 0))
    if amount > 0:
        serializer = get_log_messages_by_amount(resource_id, amount)
    else:
        dt_serializer = DateRangeSerializer(data=request.query_params)
        dt_serializer.is_valid(raise_exception=True)

        from_date = dt_serializer.validated_data.get('from_date')
        to_date   = dt_serializer.validated_data.get('to_date') # can be None

        serializer = get_log_messages_by_date(resource_id, from_date, to_date)

    if serializer is None: # add general errors later? then maybe admin could view those
        return Response(status=status.HTTP_404_NOT_FOUND)

    return Response(serializer.data, status=status.HTTP_200_OK)
