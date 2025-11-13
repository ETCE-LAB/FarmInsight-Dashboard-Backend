import uuid
import requests
from rest_framework import status
from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import ResourceManagementModel, FPF
from farminsight_dashboard_backend.serializers.resource_management_model_serializer import ResourceManagementModelSerializer

from farminsight_dashboard_backend.utils import get_logger

def get_model_by_id(model_id:str) -> ResourceManagementModel:
    """
    Get model by id
    :param model_id:
    :return: Model
    :throws: NotFoundException
    """
    try:
        return ResourceManagementModel.objects.get(id=model_id)
    except ResourceManagementModel.DoesNotExist:
        raise NotFoundException(f'Model with id: {model_id} was not found.')

def create_model(fpf_id:str, model_data:dict) -> ResourceManagementModel:
    """
    Create a new Model by FPF ID and Model data.
    :param fpf_id: ID of the model's FPF
    :param model_data: Model data
    :return: Newly created Model instance
    """
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        raise ValueError("FPF with the given ID does not exist")

    serializer = ResourceManagementModelSerializer(data=model_data, partial=True)
    serializer.is_valid(raise_exception=True)
    resource_model = serializer.save(FPF=fpf)

    return resource_model

def update_model(model_id:str, model_data:any) -> ResourceManagementModelSerializer:
    """
    Update model by id and model data
    :param model_id: model to update
    :param model_data: new model data
    :return: Updated Camera
    """
    model = get_model_by_id(model_id)
    serializer = ResourceManagementModelSerializer(model, data=model_data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def delete_model(model: ResourceManagementModel):
    """
    Delete model
    :param model: model to delete
    """
    model.delete()


class ResourceManagementModelService:
    @staticmethod
    def get_model_params(url: str):
        try:
            response = requests.get(f"{url}/params", timeout=5)
            response.raise_for_status()
            return {"data": response.json(), "status": status.HTTP_200_OK}
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status": status.HTTP_502_BAD_GATEWAY}


    @staticmethod
    def build_model_query_params(model):
        """
        Builds query params for a ResourceManagementModel's /farm-insight call.
        Replaces sensor-type params with their latest InfluxDB value.
        Returns a query string like '?roof_size=10&current_water_amount=5.4'
        """
        from urllib.parse import urlencode
        from farminsight_dashboard_backend.services import InfluxDBManager

        params = {}
        influx = InfluxDBManager.get_instance()

        for param in model.required_parameters:
            name = param.get("name")
            param_type = param.get("type")
            value = param.get("value")

            if not name or value is None:
                continue

            # Static → direct value
            if param_type == "static":
                params[name] = value

            # Sensor → fetch latest measurement
            elif param_type == "sensor":
                try:
                    sensor_id = str(value)
                    latest = influx.fetch_latest_sensor_measurements(
                        fpf_id=str(model.FPF.id),
                        sensor_ids=[sensor_id]
                    )
                    if sensor_id in latest:
                        params[name] = latest[sensor_id]["value"]
                except Exception as e:
                    print(f"⚠️ Failed to fetch sensor value for {name}: {e}")

        return f"?{urlencode(params)}" if params else ""
