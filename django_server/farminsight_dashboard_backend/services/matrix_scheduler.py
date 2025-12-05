from django_server.matrix_notifier import matrix_client
from farminsight_dashboard_backend.utils import get_logger


class MatrixScheduler:
    _instance = None

    def __init__(self):
        self.log = get_logger()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self):
        matrix_client.start_in_thread()
        self.log.debug("Matrix Client started.")
