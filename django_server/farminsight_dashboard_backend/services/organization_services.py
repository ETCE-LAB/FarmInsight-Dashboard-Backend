from django.core.exceptions import PermissionDenied

from farminsight_dashboard_backend.models import Organization, GrowingCycle, Harvest, ControllableAction
from farminsight_dashboard_backend.models import Membership, MembershipRole, FPF, Sensor, Camera
from farminsight_dashboard_backend.serializers import OrganizationSerializer
from farminsight_dashboard_backend.services.membership_services import is_admin


def create_organization(data, user) -> OrganizationSerializer:
    serializer = OrganizationSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        org = serializer.save()
        Membership.objects.create(organization=org, userprofile=user, membershipRole=MembershipRole.Admin.value)
    return serializer


def get_organization_by_id(org_id: str) -> Organization:
    org = Organization.objects.filter(id=org_id).prefetch_related('membership_set', 'membership_set__userprofile', 'fpf_set').first()
    return org


def get_organization_by_membership_id(membership_id: str) -> Organization:
    org = Membership.objects.filter(id=membership_id).first().organization
    return org


def get_organization_by_fpf_id(fpf_id) -> Organization:
    org = FPF.objects.select_related('organization').get(id=fpf_id).organization
    return org


def get_organization_by_growing_cycle_id(growing_cycle_id) -> Organization:
    org = GrowingCycle.objects.get(id=growing_cycle_id).FPF.organization
    return org


def get_organization_by_sensor_id(sensor_id) -> Organization:
    org = Sensor.objects.select_related('FPF').get(id=sensor_id).FPF.organization
    return org


def get_organization_by_camera_id(camera_id) -> Organization:
    org = Camera.objects.select_related('FPF').get(id=camera_id).FPF.organization
    return org


def get_organization_by_harvest_id(harvest_id) -> Organization:
    org = Harvest.objects.get(id=harvest_id).growingCycle.FPF.organization
    return org

def get_organization_by_controllable_action_id(controllable_action_id) -> Organization:
    org = ControllableAction.objects.select_related('FPF').get(id=controllable_action_id).FPF.organization
    return org

def update_organization(org_id, data) -> OrganizationSerializer:
    """
    Update the given organization with the given data if the user has sufficient permissions.
    :param org_id: organization id to update
    :param data: new organization data
    :return:
    """
    organization = Organization.objects.get(id=org_id)
    serializer = OrganizationSerializer(organization, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer
