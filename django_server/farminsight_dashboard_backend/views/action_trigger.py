from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.serializers import ActionTriggerSerializer
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.services import get_fpf_by_id, \
    get_organization_by_fpf_id, is_admin, create_action_trigger

logger = get_logger()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_action_trigger(request):
    """
    An admin creates a new action trigger for a controllable action
    :param request:
    :return:
    """
    fpf_id = request.data.get('fpfId')

    if not is_admin(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    get_fpf_by_id(fpf_id)

    trigger = create_action_trigger(request.data)
    serialized = ActionTriggerSerializer(trigger)

    logger.info("Action trigger created successfully", extra={'resource_id': fpf_id})

    return Response(serialized.data, status=status.HTTP_201_CREATED)