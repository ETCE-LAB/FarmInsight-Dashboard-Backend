from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from farminsight_dashboard_backend.services import is_member, get_organization_by_fpf_id, get_action_queue_by_fpf_id, \
    get_available_action_script_types_by_fpf_id


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_action_script_types(request, fpf_id):
    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    data = get_available_action_script_types_by_fpf_id(fpf_id)
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_action_queue(request, fpf_id):
    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    data = get_action_queue_by_fpf_id(fpf_id)
    return Response(data, status=status.HTTP_200_OK)
