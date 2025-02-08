from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farminsight_dashboard_backend.services import create_growing_cycle, update_growing_cycle, remove_growing_cycle, get_growing_cycles_by_fpf_id


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_growing_cycle(request):
    growing_cycle = create_growing_cycle(request.data, request.user)
    return Response(growing_cycle.data, status=status.HTTP_201_CREATED)


class GrowingCycleEditViews(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, growing_cycle_id):
        growing_cycle = update_growing_cycle(growing_cycle_id, request.data, request.user)
        return Response(growing_cycle.data, status=status.HTTP_200_OK)

    def delete(self, request, growing_cycle_id):
        remove_growing_cycle(growing_cycle_id, request.user)
        return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def get_growing_cycles(request, fpf_id):
    serializer = get_growing_cycles_by_fpf_id(fpf_id)
    return Response(serializer.data, status=status.HTTP_200_OK)