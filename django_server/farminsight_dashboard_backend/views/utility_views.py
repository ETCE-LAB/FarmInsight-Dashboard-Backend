import time
from json import JSONDecodeError

import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN, HTTP_200_OK

from farminsight_dashboard_backend.services import get_sensor, is_member, get_organization_by_sensor_id, get_sensor_hardware_configuration


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_direct_ping(request, resource_type, resource_id):
    response = None
    if resource_type == 'sensor':
        if not is_member(request.user, get_organization_by_sensor_id(resource_id)):
            return Response(status=HTTP_403_FORBIDDEN)

        sensor = get_sensor(resource_id)
        hardware_configuration = get_sensor_hardware_configuration(sensor)
        if not ('additionalInformation' in hardware_configuration and 'http' in hardware_configuration['additionalInformation']):
            return Response(data={'error': 'Sensors hardware configuration malformed, no ping possible.'}, status=HTTP_404_NOT_FOUND)

        url = hardware_configuration['additionalInformation']['http']

        response_raw = ''
        try:
            response_raw = requests.get(url, timeout=10)
            response = response_raw.json()
        except JSONDecodeError:
            response = {'return': response_raw.text}
        except Exception as e:
            return Response(data={'error': f'{e}'}, status=HTTP_200_OK)
    else:
        return Response(status=HTTP_404_NOT_FOUND)

    return Response(data=response, status=HTTP_200_OK)
