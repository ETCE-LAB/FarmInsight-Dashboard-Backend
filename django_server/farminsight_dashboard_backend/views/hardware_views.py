from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import HardwareSerializer
from farminsight_dashboard_backend.services import is_member, get_organization_by_fpf_id, \
    get_hardware_for_fpf, is_admin, set_hardware_order, get_organization_by_hardware_id, update_hardware, \
    remove_hardware, create_hardware

logger = get_logger()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fpf_hardware(request, fpf_id):
    """
    Members get all available hardware information for the given FPF.
    """
    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    hardware = get_hardware_for_fpf(fpf_id)
    serializer = HardwareSerializer(hardware, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_hardware_order(request, fpf_id):
    if not is_admin(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    set_hardware_order(request.data)

    return Response(status=status.HTTP_200_OK)


class HardwareEditViews(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, hardware_id):
        if not is_member(request.user, get_organization_by_hardware_id(hardware_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        hardware = update_hardware(hardware_id, request.data)
        return Response(hardware.data, status=status.HTTP_200_OK)

    def delete(self, request, hardware_id):
        if not is_member(request.user, get_organization_by_hardware_id(hardware_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        remove_hardware(hardware_id)
        return Response(status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_hardware(request):
    if not is_member(request.user, get_organization_by_fpf_id(request.data['FPF'])):
        return Response(status=status.HTTP_403_FORBIDDEN)

    harvest = create_hardware(request.data)
    return Response(harvest.data, status=status.HTTP_201_CREATED)
