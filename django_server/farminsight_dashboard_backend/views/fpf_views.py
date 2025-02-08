from farminsight_dashboard_backend.serializers import FPFFullSerializer
from farminsight_dashboard_backend.services import create_fpf, get_fpf_by_id, update_fpf_api_key, \
    get_visible_fpf_preview, is_member, get_organization_by_fpf_id, update_fpf
from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated, AllowAny


class FpfView(views.APIView):
    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        elif self.request.method == 'GET':
            return [AllowAny()]  # No authentication required for GET
        return super().get_permissions()

    def put(self, request, fpf_id):
        """
        Only an Admin or a SysAdmin can update an FPF
        :param request:
        :param fpf_id:
        :return:
        """
        fpf = update_fpf(fpf_id, request.data, request.user)
        return Response(fpf.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = create_fpf(request.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, fpf_id):
        fpf = FPFFullSerializer(get_fpf_by_id(fpf_id))
        if not (is_member(request.user, get_organization_by_fpf_id(fpf_id).id) or fpf.data['isPublic']):
            return Response(status=status.HTTP_403_FORBIDDEN)
        return Response(fpf.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_fpf_api_key(request, fpf_id):
    """
    Generate a new apiKey and try to send it to the FPF.
    On success, save the new key in the database.
    :param request: 
    :param fpf_id: 
    :return: 
    """
    update_fpf_api_key(fpf_id)
    
    return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def get_visible_fpf(request):
    """
    Returns List of all FPFs visible to the user includes non public ones that user is member of
    :param request:
    :return:
    """
    user = None
    if request.user.is_authenticated:
        user = request.user
    serializer = get_visible_fpf_preview(user)
    return Response(serializer.data, status=status.HTTP_200_OK)