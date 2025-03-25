from datetime import datetime

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from farminsight_dashboard_backend.services import valid_api_key_for_sensor, valid_api_key_for_fpf, write_log_message


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
