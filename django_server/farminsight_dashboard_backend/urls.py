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
)

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

    path('locations', LocationView.post_location, name='post_location'),
    path('locations/<str:location_id>', LocationView.as_view(), name='location_operations'),
    path('locations/organization/<str:organization_id>', LocationView.get_all_locations_for_organization, name='get_locations_by_organization_id'),
    path('locations/<str:location_id>/details', get_location, name='get_location_by_id'),





]

