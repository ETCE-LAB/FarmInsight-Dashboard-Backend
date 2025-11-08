from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.models import FPF, ResourceManagementModel
from farminsight_dashboard_backend.serializers.resource_management_model_serializer import ResourceManagementModelSerializer
from farminsight_dashboard_backend.services import is_member, is_admin, get_organization_by_id, get_fpf_by_id, \
    get_organization_by_fpf_id, create_action_mappings, ModelScheduler, get_organization_by_model_id
from farminsight_dashboard_backend.services.resource_management_model_services import get_model_by_id, \
    update_model, delete_model, create_model, ResourceManagementModelService
from farminsight_dashboard_backend.utils import get_logger


logger = get_logger()

class ResourceManagementModelView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, model_id):
        """
        Get a model by its id
        :param request:
        :param model:
        :return:
        """
        return Response(ResourceManagementModelSerializer(get_model_by_id(model_id)).data, status=status.HTTP_200_OK)

    def put(self, request, model_id):
        """
        If incoming model data is valid, update the _model by given id with the incoming data
        :param request:
        :param model_id: id of the _model to update
        :return:
        """
        if not is_member(request.user, get_organization_by_model_id(model_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = update_model(model_id, request.data)

        logger.info(" model updated successfully", extra={'resource_id': model_id})

        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, model_id):
        """
        Delete a _model by given id and the associated job
        :param request:
        :param _model_id:
        :return:
        """
        _model = get_model_by_id(model_id)

        if not is_admin(request.user, get_organization_by_model_id(model_id)):
            return Response(status=status.HTTP_403_FORBIDDEN)

        delete_model(_model)

        logger.info(" model deleted successfully")

        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def post_model(request):
    """
    Create a new  model
    :param request:
    :return:
    """
    fpf_id = request.data.get('fpfId')
    if not fpf_id:
        return Response({"error": "Missing fpfId"}, status=status.HTTP_400_BAD_REQUEST)

    # Security check
    if not is_member(request.user, get_organization_by_fpf_id(fpf_id)):
        return Response(status=status.HTTP_403_FORBIDDEN)

    try:
        # Create the model itself
        resource_model = create_model(fpf_id, request.data)
        logger.info(f"Model '{resource_model.name}' created successfully")

        # Handle related actions if present
        actions_data = request.data.get("actions", [])
        if actions_data:
            create_action_mappings(fpf_id, resource_model.id, actions_data)
            logger.info(f"Actions created successfully for model {resource_model.name}")

        resource_model = create_model(fpf_id, request.data)
        ModelScheduler.get_instance().add_model_job(resource_model.id)

        # Serialize for response
        response_data = ResourceManagementModelSerializer(resource_model).data
        return Response(response_data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error creating model: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_forecasts(request, fpf_id: str):
    """
    Return combined forecasts for all active ResourceManagementModels belonging to a given FPF.
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        return Response({"error": "FPF not found"}, status=status.HTTP_404_NOT_FOUND)

    # Query all active models for this FPF
    models = ResourceManagementModel.objects.filter(FPF=fpf, isActive=True)

    combined_forecasts = []

    from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
    influx = InfluxDBManager.get_instance()

    for model in models:
        if model.forecasts:
            forecast = influx.fetch_latest_model_forecast(fpf_id=fpf_id, model_id=model.id)
            combined_forecasts.append(forecast)

    if not combined_forecasts:
        return Response(
            {"message": "No forecasts available for active models under this FPF."},
            status=status.HTTP_204_NO_CONTENT
        )

    return Response({"fpf_id": fpf_id, "models": combined_forecasts}, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def set_active_scenario(request, model_id: str):
    """
    Sets the active scenario for a specific ResourceManagementModel.
    Expects JSON body: {"activeScenario": "<scenario_name>"}
    """
    try:
        model = ResourceManagementModel.objects.get(id=model_id)
    except ResourceManagementModel.DoesNotExist:
        return Response({"error": "Model not found"}, status=status.HTTP_404_NOT_FOUND)

    scenario_name = request.data.get("activeScenario")
    if not scenario_name:
        return Response({"error": "Missing 'activeScenario' field"}, status=status.HTTP_400_BAD_REQUEST)

    # normalize availableScenarios → handle list of strings or list of dicts
    available_raw = model.availableScenarios or []
    available = []
    for s in available_raw:
        if isinstance(s, dict):
            # assume {"name": "best-case"} or similar
            val = s.get("name")
            if val:
                available.append(str(val).lower())
        else:
            available.append(str(s).lower())

    # validate
    if scenario_name.lower() not in available:
        return Response(
            {
                "error": f"Invalid scenario '{scenario_name}'.",
                "available": model.availableScenarios,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    model.activeScenario = scenario_name
    model.save(update_fields=["activeScenario"])

    serializer = ResourceManagementModelSerializer(model)
    return Response(serializer.data, status=status.HTTP_200_OK)


class ModelParamsView(views.APIView):
    def get(self, request):
        url = request.data.get("URL")
        if not url:
            return Response({"error": "Missing 'URL' field"}, status=status.HTTP_400_BAD_REQUEST)

        result = ResourceManagementModelService.get_model_params(url)
        return Response(result.get("data") or {"error": result.get("error")}, status=result["status"])