from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from farminsight_dashboard_backend.serializers import OrganizationFullSerializer
from farminsight_dashboard_backend.services import create_organization, get_memberships, get_organization_by_id, \
    update_organization, is_member, is_system_admin, set_organization_order, all_organizations
from farminsight_dashboard_backend.utils import get_logger


logger = get_logger()


class OrganizationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, organization_id):
        org = get_organization_by_id(organization_id)

        if not is_member(request.user, org):
            logger.warning(f"Unauthorized attempt to access organization by user '{request.user.name}'")
            return Response(status=status.HTTP_403_FORBIDDEN)

        if org is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(OrganizationFullSerializer(org).data)

    def put(self, request, organization_id):
        """
        The user must be authenticated and an admin of the organization (or a systemAdmin) to edit it.
        :param request:
        :param organization_id:
        :return:
        """
        if not is_member(request.user, get_organization_by_id(organization_id)):
            logger.warning(f"Unauthorized attempt to update organization by user '{request.user.name}'")
            return Response(status=status.HTTP_403_FORBIDDEN)

        organization = update_organization(organization_id, request.data)
        logger.info(f"Organization '{organization.data.get('name')}' updated by user '{request.user.name}'", extra={'resource_id': organization_id})
        return Response(organization.data, status=status.HTTP_200_OK)


@api_view(['POST'])
#@permission_classes([IsAuthenticated])
def post_organization(request):
    org = create_organization(request.data, request.user)
    logger.info(f"Organization '{org.data.get('name')}' created by user '{request.user.name}'", extra={'resource_id': org.data.get('id')})
    return Response(org.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def get_own_organizations(request):
    memberships = get_memberships(request.user)
    data = []
    for membership in memberships:
        data.append({
            'id': membership.organization.id,
            'name': membership.organization.name,
            'membership': {
                'id': membership.id,
                'role': membership.membershipRole,
            }
        })
    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_organizations(request):
    if not is_system_admin(request.user):
        logger.warning(f"Unauthorized attempt to access all organizations by user '{request.user.name}'")
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = all_organizations()

    return Response(data=serializer.data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_organization_order(request):
    if not is_system_admin(request.user):
        logger.warning(f"Unauthorized attempt to reorder organizations by user '{request.user.name}'")
        return Response(status=status.HTTP_403_FORBIDDEN)

    serializer = set_organization_order(request.data)
    logger.info(f"Organization order updated by user '{request.user.name}'")

    return Response(data=serializer.data, status=status.HTTP_200_OK)