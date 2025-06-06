import datetime

from django.conf import settings
from django.utils import timezone

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import FPF, Userprofile
from farminsight_dashboard_backend.serializers import FPFSerializer, FPFPreviewSerializer, FPFFunctionalSerializer
from farminsight_dashboard_backend.utils import generate_random_api_key
from farminsight_dashboard_backend.services.organization_services import get_organization_by_fpf_id
from farminsight_dashboard_backend.services.membership_services import get_memberships, is_member


def create_fpf(data) -> FPFSerializer:
    """
    First, save fpf to database and create a new bucket in the influxdb.
    Try to send the FPF id and a new apiKey to the FPF.
    Try to send
    :param data:
    :return:
    """
    from farminsight_dashboard_backend.services import InfluxDBManager, post_fpf_id

    serializer = FPFSerializer(data=data, partial=True)

    if serializer.is_valid(raise_exception=True):
        serializer.save()
        fpf_id = serializer.data.get('id')
        try:
            update_fpf_api_key(fpf_id)
            post_fpf_id(fpf_id)
        except Exception as api_error:
            instance = serializer.instance
            if instance:
                instance.delete()
            raise api_error

        InfluxDBManager.get_instance().sync_fpf_buckets()

    return serializer


def update_fpf(fpf_id, data):
    """
    Only an Admin or an SysAdmin can update the FPF
    :param fpf_id:
    :param data:
    :return:
    """
    fpf = FPF.objects.get(id=fpf_id)
    serializer = FPFFunctionalSerializer(fpf, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        return serializer


def get_fpf_by_id(fpf_id: str):
    fpf = FPF.objects.filter(id=fpf_id).prefetch_related('sensors', 'cameras', 'growingCycles').first()
    if fpf is None:
        raise NotFoundException(f'FPF with id: {fpf_id} was not found.')
    return fpf


def is_user_part_of_fpf(fpf_id:str, user:Userprofile) -> bool:
    return is_member(user, get_organization_by_fpf_id(fpf_id))


def update_fpf_api_key(fpf_id):
    """
    Generate a new apiKey and try to send it to the given FPF.
    On success, save the new key and an apiKeyValidUntil in the database.
    :param fpf_id:
    :return:
    """
    from farminsight_dashboard_backend.services import post_fpf_api_key
    key = generate_random_api_key()
    post_fpf_api_key(fpf_id, key)
    fpf = FPF.objects.get(id=fpf_id)
    fpf.apiKey = key
    if settings.API_KEY_VALIDATION_DURATION_DAYS > 0:
        fpf.apiKeyValidUntil = timezone.now() + datetime.timedelta(days=settings.API_KEY_VALIDATION_DURATION_DAYS)
    fpf.save()


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


def set_fpf_order(ids: list[str]):
    items = FPF.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    FPF.objects.bulk_update(items, ['orderIndex'])