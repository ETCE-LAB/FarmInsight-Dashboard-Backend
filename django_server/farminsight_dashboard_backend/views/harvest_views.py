from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farminsight_dashboard_backend.services import create_harvest, update_harvest, remove_harvest, get_harvests_by_growing_cycle_id


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_harvest(request):
    harvest = create_harvest(request.data, request.user)
    return Response(harvest.data, status=status.HTTP_201_CREATED)


class HarvestEditViews(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, harvest_id):
        harvest = update_harvest(harvest_id, request.data, request.user)
        return Response(harvest.data, status=status.HTTP_200_OK)

    def delete(self, request, harvest_id):
        remove_harvest(harvest_id, request.user)
        return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def get_harvests(request, growing_cycle_id):
    serializer = get_harvests_by_growing_cycle_id(growing_cycle_id)
    return Response(serializer.data, status=status.HTTP_200_OK)