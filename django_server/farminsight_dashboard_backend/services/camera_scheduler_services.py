import logging
import threading
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone

from farminsight_dashboard_backend.models import Camera
from farminsight_dashboard_backend.services import get_camera_by_id
from farminsight_dashboard_backend.services.fpf_connection_services import fetch_camera_snapshot

class CameraScheduler:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __new__(cls, *args, **kwargs):
        return super(CameraScheduler, cls).__new__(cls)

    def __init__(self):
        """
        Initialize the CameraScheduler
        """
        if not getattr(self, "_initialized", False):
            self._scheduler = BackgroundScheduler()
            self.log = logging.getLogger("farminsight_dashboard_backend")
            self._initialized = True

    def start(self):
        """
        Start the scheduler
        :return:
        """
        self._add_all_camera_jobs()
        self._scheduler.start()

        self.log.info("CameraScheduler started.")

    def add_camera_job(self, camera_id: str):
        """
        Add a snapshot task for a specific camera.
        :param camera_id: ID of the camera
        """
        try:
            camera = get_camera_by_id(camera_id)
            if camera.isActive:
                interval = camera.intervalSeconds
                self._scheduler.add_job(
                    fetch_camera_snapshot,
                    trigger=IntervalTrigger(seconds=interval),
                    args=[camera.id, camera.snapshotUrl],
                    id=f"camera_{camera.id}_snapshot",
                    replace_existing=True,
                    next_run_time=timezone.now() + timedelta(seconds=1)
                )
                self.log.info(f"Camera {camera.id} snapshot task scheduled with interval {interval} seconds.")
        except Camera.DoesNotExist:
            self.log.warning(f"Camera with ID {camera_id} does not exist or is not active.")

    def remove_camera_job(self, camera_id: str):
        """
        Remove a snapshot task for a specific camera.
        :param camera_id:
        :return:
        """
        try:
            camera = Camera.objects.get(id=camera_id, isActive=True)
            if camera.isActive:
                self._scheduler.remove_job(job_id=f"camera_{camera.id}_snapshot")
                self.log.info(f"Camera {camera.id} snapshot task deleted.")
        except Camera.DoesNotExist:
            self.log.warning(f"Camera with ID {camera_id} does not exist or is not active.")

    def reschedule_camera_job(self, camera_id: str, new_interval: int):
        """
        Reschedule an existing snapshot task with a new interval.
        :param camera_id: ID of the camera
        :param new_interval: New interval in seconds
        """
        try:
            job_id = f"camera_{camera_id}_snapshot"

            # Check if the job exists
            existing_job = self._scheduler.get_job(job_id=job_id)

            if existing_job:
                # Remove the existing job
                self._scheduler.remove_job(job_id=job_id)
                self.log.info(f"Existing job for camera {camera_id} removed.")

            # Add a new job with the updated interval
            camera = get_camera_by_id(camera_id)
            if camera.isActive:
                self._scheduler.add_job(
                    fetch_camera_snapshot,
                    trigger=IntervalTrigger(seconds=new_interval),
                    args=[camera.id, camera.snapshotUrl],
                    id=job_id,
                    replace_existing=True,
                    next_run_time=timezone.now() + timedelta(seconds=1)
                )
                self.log.info(f"Camera {camera.id} snapshot task rescheduled with new interval {new_interval} seconds.")
            else:
                self.log.warning(f"Camera {camera_id} is not active. Cannot reschedule task.")
        except Camera.DoesNotExist:
            self.log.warning(f"Camera with ID {camera_id} does not exist. Cannot reschedule task.")

    def _add_all_camera_jobs(self):
        """
        Add snapshot tasks for all active cameras.
        """
        cameras = Camera.objects.filter(isActive=True)
        for camera in cameras:
            self.add_camera_job(str(camera.id))
