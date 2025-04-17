from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from farminsight_dashboard_backend.serializers import UserprofileSerializer
from farminsight_dashboard_backend.services import search_userprofiles, update_userprofile_name, \
    get_memberships_by_organization
from rest_framework.decorators import api_view, permission_classes


class UserprofileView(APIView):
    #permission_classes = [IsAuthenticated]

    def get(self, request, identifier):
        """
        Search userprofile by string (name or email)
        Exclude userprofiles of an organization optionally with query param exclude_organization_id.
        :param identifier: Name or email to be searched for
        :param request:
        :return:
        """
        exclude_organization_id = request.query_params.get("exclude_organization_id", None)
        userprofiles = search_userprofiles(identifier)

        if exclude_organization_id:
            memberships_to_exclude = get_memberships_by_organization(exclude_organization_id)
            userprofile_ids_to_exclude = memberships_to_exclude.values_list('userprofile_id', flat=True)
            userprofiles = userprofiles.exclude(id__in=userprofile_ids_to_exclude)

        return Response(UserprofileSerializer(userprofiles[:10], many=True).data)

    def put(self, request, identifier):
        if str(request.user.id) != identifier:
            return Response(status=status.HTTP_403_FORBIDDEN)

        updated_userprofile = update_userprofile_name(identifier, request.data.get('name'))
        return Response(UserprofileSerializer(updated_userprofile).data)


@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def get_userprofile(request):
    return Response(UserprofileSerializer(request.user).data)
