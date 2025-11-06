from rest_framework import views, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from ..serializers.tank_soil_forecast_serializer import ForecastResponseSerializer, ForecastWrappedResponseSerializer
from ..service.model_forecast import model_forecast
from ..utils.response_wrapper import response_wrapper


class ModelView(views.APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return super().get_permissions()


MODEL_FORECAST_PARAMS = [
    "latitude",
    "longitude",
    "forecast_days",
    "tank_capacity_liters",
    "starting_tank_volume",
    "soil_threshold",
]

MODEL_CASES = ["best-case", "average-case", "worst-case"]

MODEL_ACTIONS = [{"name": "watering", "type": "float"}]

MODEL_FORECASTS = [{"name": "tank-level"}, {"name": "soil-moisture"}]

MODEL_FORECAST_PARAM_DEFS = [
    {"name": "latitude", "type": "float", "required": True},
    {"name": "longitude", "type": "float", "required": True},
    {"name": "forecast_days", "type": "int", "required": True},
    {"name": "tank_capacity_liters", "type": "int", "required": True},
    {"name": "starting_tank_volume", "type": "int", "required": True},
    {"name": "soil_threshold", "type": "float", "required": True},
]


@api_view(['GET'])
@permission_classes([AllowAny])
def get_model_forecast(request) -> Response:
    """
    Generate the MODEL_FORECAST and send it to the Dashboard
    :param latitude:
    :param longitude:
    :param forecast_days:
    :param tank_capacity_liters:
    :param starting_tank_volume:
    :param soil_threshold:
    """

    params = {}
    for name in MODEL_FORECAST_PARAMS:
        value = request.query_params.get(name)
        if value is None:
            return Response({"error": f"Missing parameter: {name}"}, status=status.HTTP_400_BAD_REQUEST)
        params[name] = value

    latitude = float(params.get("latitude"))
    longitude = float(params.get("longitude"))
    forecast_days = int(params.get("forecast_days"))

    tank_capacity_liters = int(params.get("tank_capacity_liters"))
    starting_tank_volume = int(params.get("starting_tank_volume"))
    soil_threshold = float(params.get("soil_threshold"))

    forecast = model_forecast(latitude,
                              longitude,
                              forecast_days,
                              tank_capacity_liters,
                              starting_tank_volume,
                              soil_threshold)

    response = response_wrapper(forecast)

    # result_serializer = ForecastResponseSerializer(data=forecast)
    result_serializer = ForecastWrappedResponseSerializer(data=response)
    result_serializer.is_valid(raise_exception=True)

    return Response(result_serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_model_params_list(request) -> Response:
    return Response(
        [{"input_parameters": MODEL_FORECAST_PARAM_DEFS},
         {"scenarios": [{"name": s} for s in MODEL_CASES]},
         {"actions": MODEL_ACTIONS},
         {"forecasts": MODEL_FORECASTS}
         ], status=status.HTTP_200_OK)
