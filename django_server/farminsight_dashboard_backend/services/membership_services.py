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


def update_membership(membership_id: str, new_membership_role: str, requesting_user: Userprofile) -> MembershipSerializer:
    """
    An Admin of the Organization, or System Admin of the Backend can promote a user.
    :param membership_id:
    :param new_membership_role:
    :param requesting_user:
    :return: success
    """
    try:
        membership = Membership.objects.select_related('userprofile').get(id=membership_id)
    except Membership.DoesNotExist:
        raise NotFoundException(f'Membership {membership_id} not found.')

    if new_membership_role == MembershipRole.Member:
        can_update = False
        if is_system_admin(requesting_user) or not membership.userprofile.is_active:
            can_update = True
    else:
        can_update = True

    if can_update:
        membership.membershipRole = new_membership_role
        membership.save()
        return MembershipSerializer(membership)

    raise PermissionDenied()


def remove_membership(membership_id) -> bool:
    try:
        membership = Membership.objects.get(id=membership_id)
    except Membership.DoesNotExist:
        raise NotFoundException(f'Membership {membership_id} not found.')

    if membership.membershipRole == MembershipRole.Admin:
        return False

    membership.delete()
    return True


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
    return getattr(user, "systemRole", None) == SystemRole.SystemAdmin.value


def get_memberships_by_organization(organization_id):
    return Membership.objects.filter(organization_id=organization_id)
