from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farminsight_dashboard_backend.services import create_threshold, update_threshold, remove_threshold, \
    is_member, get_organization_by_sensor_id, get_organization_by_threshold_id


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_threshold(request):
    if not is_member(request.user, get_organization_by_sensor_id(request.data['sensorId'])):
        return Response(status=status.HTTP_403_FORBIDDEN)

    threshold = create_threshold(request.data)
    return Response(threshold.data, status=status.HTTP_201_CREATED)


class ThresholdEditViews(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, threshold_id):
        if not is_member(request.user, get_organization_by_sensor_id(request.data['sensorId'])):
            return Response(status=status.HTTP_403_FORBIDDEN)

        threshold = update_threshold(threshold_id, request.data)
        return Response(threshold.data, status=status.HTTP_200_OK)

    def delete(self, request, threshold_id):
        if not is_member(request.user, get_organization_by_threshold_id(threshold_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        remove_threshold(threshold_id)
        return Response(status=status.HTTP_200_OK)
