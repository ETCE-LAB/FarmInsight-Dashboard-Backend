from django.db.models import QuerySet
from django.core.exceptions import PermissionDenied

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.serializers import MembershipSerializer
from farminsight_dashboard_backend.models import Userprofile, Membership, MembershipRole, SystemRole


def get_memberships(user: Userprofile) -> QuerySet[Membership]:
    return Membership.objects.filter(userprofile_id=user.id).prefetch_related('organization').all()


def create_membership(user: Userprofile, data: dict) -> MembershipSerializer:
    if is_admin(user, data['organizationId']):
        membership_serializer = MembershipSerializer(data=data)
        if membership_serializer.is_valid(raise_exception=True):
            membership_serializer.save()

        return membership_serializer
    raise PermissionDenied()


def update_membership(membership_id, creating_user, new_membership_role):
    """
    An Admin of the Organization, or System Admin of the Backend can promote a user.
    :param membership_id:
    :param creating_user:
    :param new_membership_role:
    :return:
    """
    try:
        membership = Membership.objects.get(id=membership_id)
    except Membership.DoesNotExist:
        raise NotFoundException(f'Membership {membership_id} not found.')

    if is_admin(creating_user, membership.organization_id):
        membership.membershipRole = new_membership_role
        membership.save()
        return
    raise PermissionDenied()


def remove_membership(membership_id, user):
    """
    Only an admin can delete a user.
    :param membership_id:
    :param user:
    :return:
    """
    try:
        membership = Membership.objects.get(id=membership_id)
    except Membership.DoesNotExist:
        raise NotFoundException(f'Membership {membership_id} not found.')

    if is_admin(user, membership.organization_id):
        membership.delete()
        return
    raise PermissionDenied()


def is_member(user, organization_id):
    memberships = get_memberships(user)
    organization_ids = memberships.values_list('organization_id', flat=True)
    if organization_id not in organization_ids:
        return False
    return True
  

def is_admin(user, organization_id):
    membership = Membership.objects.filter(userprofile_id=user.id, organization_id=organization_id, membershipRole=MembershipRole.Admin.value).first()
    if membership is not None:
        return True

    return user.systemRole == SystemRole.SystemAdmin.value


def get_memberships_by_organization(organization_id):
    return Membership.objects.filter(organization_id=organization_id)
