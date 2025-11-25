from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_200_OK

from farminsight_dashboard_backend.services import get_value_ping, get_sensor


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_direct_ping(request, resource_type, resource_id):
    if resource_type == 'sensor':
        fpf_id = get_sensor(resource_id).FPF_id
        response = get_value_ping(str(fpf_id), resource_id)
    else:
        return Response(status=HTTP_404_NOT_FOUND)

    return Response(data=response, status=HTTP_200_OK)
