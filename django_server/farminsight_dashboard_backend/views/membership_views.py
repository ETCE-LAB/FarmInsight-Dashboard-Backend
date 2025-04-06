from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from farminsight_dashboard_backend.serializers.update_membership_serializer import MembershipUpdateSerializer
from farminsight_dashboard_backend.services import create_membership, update_membership, remove_membership, is_admin, \
    get_organization_by_id
from farminsight_dashboard_backend.services.organization_services import get_organization_by_membership_id


class MembershipView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Create a membership
        :param request:
        :return:
        """
        if not is_admin(request.user, get_organization_by_id(request.data['organizationId'])):
            return Response(status=status.HTTP_403_FORBIDDEN)

        membership_serializer = create_membership(request.data)
        return Response(membership_serializer.data, status=status.HTTP_201_CREATED)

    def put(self, request, membership_id):
        """
        Only admins can promote users to admins
        :param request:
        :param membership_id:
        :return:
        """
        if not is_admin(request.user, get_organization_by_membership_id(membership_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        membership_role = request.data.get('membershipRole')

        serializer = MembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        update_membership(membership_id, membership_role)
        return Response(status=status.HTTP_200_OK)

    def delete(self, request, membership_id):
        """
        Only admins can delete users
        :param request:
        :param membership_id:
        :return:
        """
        if not is_admin(request.user, get_organization_by_membership_id(membership_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        remove_membership(membership_id)
        return Response(status=status.HTTP_200_OK)
