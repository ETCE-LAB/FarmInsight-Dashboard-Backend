from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.serializers import LocationFullSerializer
from farminsight_dashboard_backend.services import create_location, get_location_by_id, \
     update_location, is_member, get_organization_by_id

logger = get_logger()

class LocationView(views.APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        elif self.request.method == 'GET':
            return [AllowAny()]  # No authentication required for GET
        return super().get_permissions()

    def put(self, request, location_id):
        """
        Only an Admin or a SysAdmin can update an FPF
        :param request:
        :param location_id:
        :return:
        """
        if not is_member(request.user, get_organization_by_id(request.data['organizationId'])):
            return Response(status=status.HTTP_403_FORBIDDEN)

        location = update_location(location_id, request.data)
        logger.info('updated location', extra={'resource_id': location_id})
        return Response(location.data, status=status.HTTP_200_OK)

    def post(self, request):
        if not is_member(request.user, get_organization_by_id(request.data['organizationId'])):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = create_location(request.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, location_id):

        return Response(LocationFullSerializer(get_location_by_id(location_id)).data, status=status.HTTP_200_OK)

    def get_all_locations_for_organization(self, request, organization_id):
        """
        Get all locations for a given organization
        :param request:
        :param organization_id:
        :return:
        """
        if not is_member(request.user, get_organization_by_id(organization_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        locations = get_locations_by_organization(organization_id)

        return Response(serializer.data, status=status.HTTP_200_OK)