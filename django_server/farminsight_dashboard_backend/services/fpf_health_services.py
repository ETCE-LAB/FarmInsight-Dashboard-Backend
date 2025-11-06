from farminsight_dashboard_backend.models import FPF
# This import assumes 'get_sensor_types' is available from the 'services' package
# (e.g., defined in services/__init__.py or another services file)
from farminsight_dashboard_backend.services import get_sensor_types
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()


def check_all_fpf_health():
    """
    Checks the health of all FPFs by attempting to get sensor types
    and updates their isActive status in the database.
    """
    fpfs = FPF.objects.all()
    logger.info(f'Checking health of {len(fpfs)} FPFs...')

    for fpf in fpfs:
        is_active = False
        try:
            # We use get_sensor_types as a simple ping to the FPF.
            get_sensor_types(fpf.id)
            is_active = True
            logger.info(f'FPF {fpf.name} is online.')
        except Exception as e:
            logger.warning(f'FPF {fpf.name} is offline: {type(e).__name__}')

        # Only update the database if the status has changed
        if fpf.isActive != is_active:
            fpf.isActive = is_active
            fpf.save()

    logger.info('Successfully updated FPF health statuses.')