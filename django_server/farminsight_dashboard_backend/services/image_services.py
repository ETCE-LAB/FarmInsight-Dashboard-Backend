from farminsight_dashboard_backend.models import Image


def get_images_by_camera(camera_id, from_date, to_date=None):
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
    return images.order_by('-measuredAt')
