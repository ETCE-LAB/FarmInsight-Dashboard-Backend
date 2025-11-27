import datetime
import logging

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import FPF, Userprofile
from farminsight_dashboard_backend.serializers import FPFSerializer, FPFPreviewSerializer, FPFFunctionalSerializer
from farminsight_dashboard_backend.utils import generate_random_api_key
from farminsight_dashboard_backend.services.organization_services import get_organization_by_fpf_id
from farminsight_dashboard_backend.services.membership_services import get_memberships, is_member

logger = logging.getLogger(__name__)


def create_fpf(data) -> FPFSerializer:
    """
    First, save fpf to database and create a new bucket in the influxdb.
    Try to send the FPF id and a new apiKey to the FPF.
    Try to send
    :param data:
    :return:
    """
    from farminsight_dashboard_backend.services import InfluxDBManager, post_fpf_id

    logger.info(f"Attempting to create a new FPF with name: {data.get('name')}")
    serializer = FPFSerializer(data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        fpf_id = serializer.data.get('id')
        fpf_name = serializer.data.get('name')
        logger.info(f"New FPF '{fpf_name}' created, starting post-creation process.")
        try:
            update_fpf_api_key(fpf_id)
            post_fpf_id(fpf_id)
        except Exception as api_error:
            instance = serializer.instance
            if instance:
                instance.delete()
            logger.error(f"Error during post-creation process for FPF '{fpf_name}'. Deleting instance. Error: {api_error}")
            raise api_error

        InfluxDBManager.get_instance().sync_fpf_buckets()
        logger.info(f"Successfully created and configured FPF '{fpf_name}'.")
    else:
        logger.warning(f"FPF creation failed due to validation errors: {serializer.errors}")
        raise ValidationError(serializer.errors)

    return serializer


def update_fpf(fpf_id, data):
    """
    Only an Admin or an SysAdmin can update the FPF
    :param fpf_id:
    :param data:
    :return:
    """
    fpf = FPF.objects.get(id=fpf_id)
    logger.info(f"Attempting to update FPF: '{fpf.name}'.")
    serializer = FPFFunctionalSerializer(fpf, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        logger.info(f"FPF '{fpf.name}' has been updated successfully.")
        return serializer


def get_fpf_by_id(fpf_id: str):
    fpf = FPF.objects.filter(id=fpf_id).prefetch_related('sensors', 'cameras', 'growingCycles').first()
    if fpf is None:
        logger.warning(f"Could not find FPF with id: {fpf_id}")
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
    fpf = FPF.objects.get(id=fpf_id)
    logger.info(f"Attempting to update API key for FPF: '{fpf.name}'.")
    key = generate_random_api_key()
    post_fpf_api_key(fpf_id, key)
    fpf.apiKey = key
    if settings.API_KEY_VALIDATION_DURATION_DAYS > 0:
        fpf.apiKeyValidUntil = timezone.now() + datetime.timedelta(days=settings.API_KEY_VALIDATION_DURATION_DAYS)
    fpf.save()
    logger.info(f"FPF '{fpf.name}' received a new API key successfully.")


def get_visible_fpf_preview(user: Userprofile=None) -> FPFPreviewSerializer:
    fpfs = set()
    if user:
        memberships = get_memberships(user)
        fpfs |= set(
            fpf for membership in memberships for fpf in membership.organization.fpf_set.all()
        )
    public_fpfs = FPF.objects.filter(isPublic=True).all()
    fpfs |= set([fpf for fpf in public_fpfs])

    serializer = FPFPreviewSerializer(sorted(fpfs, key=lambda x: (x.organization.orderIndex, x.orderIndex)), many=T)
    return serializer


def set_fpf_order(ids: list[str]) -> FPFSerializer:
    logger.info(f"Attempting to update order for {len(ids)} FPFs.")
    items = FPF.objects.filter(id__in=ids)
    for item in items:
        item.orderIndex = ids.index(str(item.id))

    FPF.objects.bulk_update(items, ['orderIndex'])
    logger.info(f"Successfully updated order for {len(ids)} FPFs.")

    return FPFSerializer(items, many=True)
