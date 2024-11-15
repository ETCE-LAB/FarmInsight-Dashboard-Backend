from django.urls import path

from farminsight_dashboard_backend.views import (
    get_userprofile_by_search_string,
    get_own_organizations,
    MeasurementView,
    get_userprofile,
    post_organization,
    post_fpf,
    get_fpf_data,
    get_sensor_data, get_organization
)
from farminsight_dashboard_backend.views.membership_views import MembershipView

urlpatterns = [
    path('userprofiles', get_userprofile, name='get_userprofile'),
    path('userprofiles/<str:search_string>', get_userprofile_by_search_string, name='get_userprofile_by_search_string'),
    path('organizations/own', get_own_organizations, name='get_own_organizations'),
    path('organizations', post_organization, name='post_organization'),
    path('organizations/<str:organization_identifier>', get_organization, name='get_organization'),
    path('memberships', MembershipView.as_view(), name='post_membership'),
    path('memberships/<str:membership_id>', MembershipView.as_view(), name='membership_operations'),
    path('fpfs', post_fpf, name='post_fpf'),
    path('fpfs/<str:fpf_id>/data', get_fpf_data, name='get_fpf_data'),
    path('sensors/<str:sensor_id>/measurements', get_sensor_data, name='get_sensor_data'),
    path('sensors', SensorView.as_view(), name='post_sensor'),
    path('sensors/<str:sensor_id>', SensorView.as_view(), name='sensor_operations'),
    path('sensors/types/available/<str:fpf_id>', get_fpf_sensor_types, name='get_fpf_sensor_types'),
    path('measurements/<str:sensor_id>', MeasurementView.as_view(), name='sensor-measurements')
]
