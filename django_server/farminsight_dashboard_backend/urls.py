from django.urls import path
from .views import MeasurementView

urlpatterns = [
    path('measurements/<str:sensorId>', MeasurementView.as_view(), name='sensor-measurements'),
]
