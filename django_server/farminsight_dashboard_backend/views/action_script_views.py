from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from farminsight_dashboard_backend.action_scripts.typed_action_script_factory import TypedActionScriptFactory
from farminsight_dashboard_backend.serializers import ActionScriptDescriptionSerializer
from farminsight_dashboard_backend.services import is_member, get_organization_by_fpf_id, is_system_admin
from farminsight_dashboard_backend.utils import is_valid_uuid


typed_action_script_factory = TypedActionScriptFactory()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_action_script_types(request):
    action_script_types = typed_action_script_factory.get_available_action_scripts()
    serializer = ActionScriptDescriptionSerializer(action_script_types, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_action_queue(request, fpf_id):
    if is_valid_uuid(fpf_id):
        if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)
    else:
        if not is_system_admin(request.user):
            return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = get_action_queue(fpf_id)
    return Response(serializer.data, status=status.HTTP_200_OK)
