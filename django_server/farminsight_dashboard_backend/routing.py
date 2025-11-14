from django.urls import re_path

from farminsight_dashboard_backend.consumers import SensorUpdatesConsumer
from farminsight_dashboard_backend.consumers.ws_consumer import CameraLivestreamConsumer

websocket_urlpatterns = [
    re_path(r"ws/sensor/(?P<sensor_id>[\w-]+)", SensorUpdatesConsumer.as_asgi()),
    re_path(r"ws/camera/(?P<camera_id>[\w-]+)", CameraLivestreamConsumer.as_asgi())
]