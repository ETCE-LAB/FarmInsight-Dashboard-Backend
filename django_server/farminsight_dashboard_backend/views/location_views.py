from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import LocationSerializer
from farminsight_dashboard_backend.services import create_location, get_location_by_id, \
    update_location, is_member,  gather_locations_by_organization_id, get_organization_by_id

logger = get_logger()


@api_view(['GET'])
def get_location(request, location_id):
    return Response(LocationSerializer(get_location_by_id(location_id)).data, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_location(request):
    """
    Create a new location
    :param request:
    :return:
    """
    if not is_member(request.user, get_organization_by_id(request.data['organizationId'])):
        return Response(status=status.HTTP_403_FORBIDDEN)
    location = create_location(request.data)
    return Response(location.data, status=status.HTTP_201_CREATED)

class LocationView(APIView):


    def put(self, request, location_id):
        """
        Only an Admin or a SysAdmin can update a Location
        :param request:
        :param location_id:
        :return:
        """
        if not is_member(request.user, get_organization_by_id(request.data['organizationId'])):
            return Response(status=status.HTTP_403_FORBIDDEN)

        location = update_location(location_id, request.data)
        logger.info('updated location', extra={'resource_id': location_id})
        return Response(location.data, status=status.HTTP_200_OK)

    @api_view(['GET'])
    def get_locations_by_organization(request, organization_id):
        """
        Get all locations for a given organization
        :param request:
        :param organization_id:
        :return:
        """
        if not is_member(request.user, get_organization_by_id(organization_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        locations = gather_locations_by_organization_id(organization_id)

        return Response(locations.data, status=status.HTTP_200_OK)
