from django.urls import path

from farminsight_dashboard_backend.views import (
    get_userprofile,
    post_organization,
    post_fpf,
    get_own_organizations,
    post_membership,
    MeasurementView
)

urlpatterns = [
    path('userprofiles', get_userprofile, name='get_userprofile'),
    path('organizations', post_organization, name='post_organization'),
    path('memberships', post_membership, name='post_membership'),
    path('organizations/own', get_own_organizations, name='get_own_organizations'),
    path('fpfs', post_fpf, name='post_fpf'),
    path('measurements/<str:sensor_id>', MeasurementView.as_view(), name='sensor-measurements'),
]
