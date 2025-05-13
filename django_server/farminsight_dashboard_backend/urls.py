from django.urls import path

from farminsight_dashboard_backend.views import (
    UserprofileView,
    get_userprofile,
    get_own_organizations,
    MeasurementView,
    post_organization,
    get_fpf_data,
    get_sensor_data,
    post_growing_cycle,
    GrowingCycleEditViews,
    MembershipView,
    SensorView,
    get_fpf_sensor_types,
    FpfView,
    get_fpf_api_key,
    get_visible_fpf,
    get_websocket_token,
    post_camera,
    CameraView,
    get_camera_images,
    get_camera_livestream,
    OrganizationView,
    get_growing_cycles,
    post_harvest,
    HarvestEditViews,
    get_harvests,
    login_view,
    signup_view,
    change_password_view,
    logout_view,
    post_log_message,
    get_log_messages,
    LocationView,
    get_location,
    post_location,
    get_weather_forecasts,
    post_controllable_action,
    ControllableActionView,
    execute_controllable_action,
    get_fpf_hardware,
    post_action_trigger,
    post_threshold,
    ThresholdEditViews,
    get_available_action_script_types,
)
from farminsight_dashboard_backend.views.action_trigger import ActionTriggerView

urlpatterns = [
    path('userprofiles', get_userprofile, name='get_userprofile'),
    path('userprofiles/<str:identifier>', UserprofileView.as_view(), name='userprofile_operations'),
    path('organizations/own', get_own_organizations, name='get_own_organizations'),
    path('organizations/<str:organization_id>', OrganizationView.as_view(), name='organization_operations'),
    path('organizations', post_organization, name='post_organization'),
    path('fpfs', FpfView.as_view(), name='post_fpf'),
    path('fpfs/visible', get_visible_fpf, name='get_visible_fpf'),
    path('fpfs/<str:fpf_id>', FpfView.as_view(), name='fpf_operations'),
    path('fpfs/<str:fpf_id>/api-key', get_fpf_api_key, name='get_fpf_api_key'),
    path('fpfs/<str:fpf_id>/data', get_fpf_data, name='get_fpf_data'),
    path('fpfs/<str:fpf_id>/hardware', get_fpf_hardware, name='get_fpf_hardware'),

    path('memberships', MembershipView.as_view(), name='post_membership'),
    path('memberships/<str:membership_id>', MembershipView.as_view(), name='membership_operations'),

    path('sensors/<str:sensor_id>/measurements', get_sensor_data, name='get_sensor_data'),
    path('sensors', SensorView.as_view(), name='post_sensor'),
    path('sensors/<str:sensor_id>', SensorView.as_view(), name='sensor_operations'),
    path('sensors/types/available/<str:fpf_id>', get_fpf_sensor_types, name='get_fpf_sensor_types'),

    path('measurements/<str:sensor_id>', MeasurementView.as_view(), name='sensor-measurements'),

    path('growing-cycles', post_growing_cycle, name='post_growing_cycle'),
    path('growing-cycles/<str:growing_cycle_id>', GrowingCycleEditViews.as_view(), name='growing_cycle_edits'),
    path('growing-cycles/list/<str:fpf_id>', get_growing_cycles, name='get_growing_cycles'),

    path('websocket-token', get_websocket_token, name='get_websocket_token'),

    path('cameras', post_camera, name='post_camera'),
    path('cameras/<str:camera_id>', CameraView.as_view(), name='camera_operations'),
    path('cameras/<str:camera_id>/livestream', get_camera_livestream, name='get_camera_livestream'),
    path('cameras/<str:camera_id>/images', get_camera_images, name='get_camera_snapshots'),

    path('harvests', post_harvest, name='post_harvest'),
    path('harvests/<str:harvest_id>', HarvestEditViews.as_view(), name='harvest_edits'),
    path('harvests/list/<str:growing_cycle_id>', get_harvests, name='get_harvests'),

    path('login/', login_view, name='login_view'),
    path('signup/', signup_view, name='signup_view'),
    path('logout', logout_view, name='logout_view'),
    path('change-password', change_password_view, name='change_password_view'),
    path('log_messages', post_log_message, name='post_log_message'),
    path('log_messages/<str:resource_type>/<str:resource_id>', get_log_messages, name='get_log_messages'),

    path('controllable-actions', post_controllable_action, name='post_controllable_action'),
    path('controllable-actions/<str:controllable_action_id>', ControllableActionView.as_view(), name='controllable_action_operations'),
    path('execute-actions/<str:controllable_action_id>/<str:trigger_id>', execute_controllable_action, name='execute_controllable_action'),
    path('action-scripts/types', get_available_action_script_types, name='get_available_action_script_types'),

    path('action-trigger', post_action_trigger,name='post_action_trigger'),
    path('action-trigger/<str:actionTrigger_id>', ActionTriggerView.as_view(), name='actionTrigger_operations'),

    path('locations', post_location, name='post_location'),
    path('locations/<str:location_id>', LocationView.as_view(), name='location_operations'),
    path('locations/organization/<str:organization_id>', LocationView.get_locations_by_organization, name='get_locations_by_organization_id'),
    path('locations/<str:location_id>/details', get_location, name='get_location'),

    path('weather-forecasts/<str:location_id>', get_weather_forecasts, name='get_weather_forecasts'),

    path('thresholds', post_threshold, name='post_threshold'),
    path('thresholds/<str:threshold_id>', ThresholdEditViews.as_view(), name='threshold_edits'),
]

