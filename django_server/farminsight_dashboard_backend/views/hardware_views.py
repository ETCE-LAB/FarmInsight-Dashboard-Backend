from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import FPFFullSerializer, HardwareSerializer
from farminsight_dashboard_backend.services import create_fpf, get_fpf_by_id, update_fpf_api_key, \
    get_visible_fpf_preview, is_member, get_organization_by_fpf_id, update_fpf, get_organization_by_id, \
    get_hardware_for_fpf, is_admin, set_hardware_order
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

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
