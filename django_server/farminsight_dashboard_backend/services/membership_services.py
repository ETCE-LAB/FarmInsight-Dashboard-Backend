from django.db.models import QuerySet
from django.core.exceptions import PermissionDenied

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.serializers import MembershipSerializer
from farminsight_dashboard_backend.models import Userprofile, Membership, MembershipRole, SystemRole, Organization


def get_memberships(user: Userprofile) -> QuerySet[Membership]:
    return Membership.objects.filter(userprofile_id=user.id).prefetch_related('organization').all()


def create_membership(data: dict) -> MembershipSerializer:
    membership_serializer = MembershipSerializer(data=data)
    if membership_serializer.is_valid(raise_exception=True):
        membership_serializer.save()

    return membership_serializer


def update_membership(membership_id, new_membership_role):
    """
    An Admin of the Organization, or System Admin of the Backend can promote a user.
    :param membership_id:
    :param new_membership_role:
    :return:
    """
    try:
        membership = Membership.objects.get(id=membership_id)
    except Membership.DoesNotExist:
        raise NotFoundException(f'Membership {membership_id} not found.')

    membership.membershipRole = new_membership_role
    membership.save()


def remove_membership(membership_id):
    """
    Only an admin can delete a user.
    :param membership_id:
    :return:
    """
    try:
        membership = Membership.objects.get(id=membership_id)
    except Membership.DoesNotExist:
        raise NotFoundException(f'Membership {membership_id} not found.')

    membership.delete()


def is_member(user, organization: Organization):
    membership = Membership.objects.filter(userprofile_id=user.id, organization=organization).first()
    if membership is not None:
        return True

    return is_system_admin(user)
  

def is_admin(user, organization: Organization):
    membership = Membership.objects.filter(userprofile_id=user.id, organization=organization, membershipRole=MembershipRole.Admin.value).first()
    if membership is not None:
        return True

    return is_system_admin(user)


def is_system_admin(user):
    return user.systemRole == SystemRole.SystemAdmin.value


def get_memberships_by_organization(organization_id):
    return Membership.objects.filter(organization_id=organization_id)
