from django.urls import re_path

from farminsight_dashboard_backend.consumers import SensorUpdatesConsumer


websocket_urlpatterns = [
    re_path(r"ws/sensor/(?P<sensor_id>[\w-]+)", SensorUpdatesConsumer.as_asgi()),
]