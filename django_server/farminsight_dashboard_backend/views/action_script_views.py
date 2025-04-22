from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView


from farminsight_dashboard_backend.action_scripts.typed_action_script_factory import TypedActionScriptFactory
from farminsight_dashboard_backend.serializers import ActionScriptDescriptionSerializer

typed_action_script_factory = TypedActionScriptFactory()

@api_view(['GET'])
#@permission_classes([IsAuthenticated])
def get_available_action_script_types(request):
    action_script_types = typed_action_script_factory.get_available_action_scripts()
    serializer = ActionScriptDescriptionSerializer(action_script_types, many=True)
    return Response(serializer.data)