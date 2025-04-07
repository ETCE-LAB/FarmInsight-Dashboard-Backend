import datetime

from django.conf import settings
from django.utils import timezone

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.models import FPF, Userprofile
from farminsight_dashboard_backend.serializers import FPFSerializer, FPFPreviewSerializer, FPFFunctionalSerializer
from farminsight_dashboard_backend.utils import generate_random_api_key
from farminsight_dashboard_backend.services.organization_services import get_organization_by_fpf_id
from farminsight_dashboard_backend.services.membership_services import get_memberships, is_member


def create_location(data) -> LocationSerializer:
    from farminsight_dashboard_backend.services import InfluxDBManager
    serializer = FPFSerializer(data=data, partial=True)

    if serializer.is_valid(raise_exception=True):
        serializer.save()
        location_id = serializer.data.get('id')
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