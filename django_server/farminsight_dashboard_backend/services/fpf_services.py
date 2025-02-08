import datetime

from django.conf import settings
from django.utils import timezone

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import FPF, Userprofile, Membership, SystemRole, MembershipRole
from farminsight_dashboard_backend.serializers import FPFSerializer, FPFPreviewSerializer, FPFFunctionalSerializer
from farminsight_dashboard_backend.utils import generate_random_api_key
from .membership_services import get_memberships
from django.core.exceptions import PermissionDenied

def create_fpf(data) -> FPFSerializer:
    """
    First, save fpf to database and create a new bucket in the influxdb.
    Try to send the FPF id and a new apiKey to the FPF.
    Try to send
    :param data:
    :return:
    """
    from farminsight_dashboard_backend.services import InfluxDBManager
    from farminsight_dashboard_backend.services import send_request_to_fpf

    serializer = FPFSerializer(data=data, partial=True)

    if serializer.is_valid(raise_exception=True):
        serializer.save()
        fpf_id = serializer.data.get('id')
        try:
            update_fpf_api_key(fpf_id)
            send_request_to_fpf(fpf_id, 'post', '/api/fpf-ids', {"fpfId": fpf_id})
        except Exception as api_error:
            instance = serializer.instance
            if instance:
                instance.delete()
            raise api_error

        InfluxDBManager.get_instance().sync_fpf_buckets()

    return serializer

def update_fpf(fpf_id, data, user):
    """
    Only an Admin or an SysAdmin can update the FPF
    :param fpf_id:
    :param data:
    :param user:
    :return:
    """
    try:
        membership = Membership.objects.get(userprofile_id=user.id)
    except Membership.DoesNotExist:
        raise NotFoundException(f'Membership {user.id} not found.')

    memberships = get_memberships(user) \
        .filter(organization_id=membership.organization.id, membershipRole=MembershipRole.Admin.value) \
        .all()

    if len(memberships) > 0 or user.systemRole == SystemRole.SystemAdmin.value:

        fpf = FPF.objects.get(id=fpf_id)
        serializer = FPFFunctionalSerializer(fpf, data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return serializer
    raise PermissionDenied()


def get_fpf_by_id(fpf_id: str):
    fpf = FPF.objects.filter(id=fpf_id).prefetch_related('sensors', 'cameras', 'growingCycles').first()
    if fpf is None:
        raise NotFoundException(f'FPF with id: {fpf_id} was not found.')
    return fpf


def is_user_part_of_fpf(fpf_id:str, user:Userprofile) -> bool:
    fpf = get_fpf_by_id(fpf_id)

    memberships = get_memberships(user).filter(organization_id=fpf.organization_id).all()
    return len(memberships) > 0


def update_fpf_api_key(fpf_id):
    """
    Generate a new apiKey and try to send it to the given FPF.
    On success, save the new key and an apiKeyValidUntil in the database.
    :param fpf_id:
    :return:
    """
    from farminsight_dashboard_backend.services import send_request_to_fpf
    key = generate_random_api_key()
    send_request_to_fpf(fpf_id, 'post', '/api/api-keys', {"apiKey": key})
    fpf = FPF.objects.get(id=fpf_id)
    fpf.apiKey = key
    if settings.API_KEY_VALIDATION_DURATION_DAYS > 0:
        fpf.apiKeyValidUntil = timezone.now() + datetime.timedelta(days=settings.API_KEY_VALIDATION_DURATION_DAYS)
    fpf.save()
    return

def get_visible_fpf_preview(user: Userprofile=None) -> FPFPreviewSerializer:
    fpfs = set()
    if user:
        memberships = get_memberships(user)
        fpfs |= set(
            fpf for membership in memberships for fpf in membership.organization.fpf_set.all()
        )
    public_fpfs = FPF.objects.filter(isPublic=True).all()
    fpfs |= set([fpf for fpf in public_fpfs])

    serializer = FPFPreviewSerializer(fpfs, many=True)
    return serializer

