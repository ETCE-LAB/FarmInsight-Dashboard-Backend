import base64
import uuid
from datetime import datetime

from django.core.files import File
from django.utils import timezone

from farminsight_dashboard_backend.models import Image
from farminsight_dashboard_backend.serializers import ImageURLSerializer


def get_images_by_camera(camera_id, from_date, to_date=None) -> ImageURLSerializer:
    """
    Retrieve snapshots for a specific camera within a given timeframe.

    :param camera_id: ID of the camera
    :param from_date: Start of the date range
    :param to_date: End of the date range (optional, defaults to now)
    :return: Queryset of Snapshot objects within the timeframe
    """
    images = Image.objects.filter(camera_id=camera_id, measuredAt__gte=from_date)
    if to_date:
        images = images.filter(measuredAt__lte=to_date)
    return ImageURLSerializer(images.order_by('-measuredAt'), many=True)


def save_image(image_b64: str, camera_id: str, created_at: datetime = timezone.now()) -> ImageURLSerializer:
    filename = f"{str(uuid.uuid4())}.jpg"
    img = Image.objects.create(
        camera_id=camera_id,
        image=File(base64.b64decode(image_b64), name=filename),
        measuredAt=created_at
    )

    return ImageURLSerializer(img)