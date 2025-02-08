from farminsight_dashboard_backend.models import Membership, MembershipRole, FPF
from farminsight_dashboard_backend.serializers import OrganizationSerializer
from farminsight_dashboard_backend.models import Organization
from django.core.exceptions import PermissionDenied


def create_organization(data, user) -> OrganizationSerializer:
    serializer = OrganizationSerializer(data=data)
    if serializer.is_valid(raise_exception=True):
        org = serializer.save()
        Membership.objects.create(organization=org, userprofile=user, membershipRole=MembershipRole.Admin.value)
    return serializer


def get_organization_by_id(id: str) -> Organization:
    org = Organization.objects.filter(id=id).prefetch_related('membership_set', 'membership_set__userprofile', 'fpf_set').first()
    return org


def get_organization_by_fpf_id(fpf_id) -> Organization:
    org = FPF.objects.select_related('organization').get(id=fpf_id).organization
    return org

def update_organization(org_id, data, user) -> OrganizationSerializer:
    """
    Update the given organization with the given data if the user has sufficient permissions.
    :param org_id: organization id to update
    :param data: new organization data
    :param user: user requesting update
    :return:
    """
    from farminsight_dashboard_backend.services import get_memberships
    memberships = get_memberships(user) \
        .filter(organization_id=org_id, membershipRole=MembershipRole.Admin.value) \
        .all()

    if len(memberships) > 0 or user.systemRole == user.SystemAdmin.value:
        organization = Organization.objects.get(id=org_id)
        serializer = OrganizationSerializer(organization, data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return serializer

    raise PermissionDenied()