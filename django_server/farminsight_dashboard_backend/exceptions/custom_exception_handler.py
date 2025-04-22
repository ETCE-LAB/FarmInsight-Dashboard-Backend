from rest_framework.exceptions import APIException
from rest_framework import status


class NotFoundException(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_code = "not_found"

    def __init__(self, detail=None):
        if detail is None:
            detail = "The requested resource was not found."
        self.detail = detail


class InfluxDBNoConnectionException(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Failed to connect to InfluxDB."
    default_code = "influxdb_connection_error"


class InfluxDBQueryException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to retrieve sensor measurements due to an InfluxDB error."
    default_code = "influxdb_query_error"

class InfluxDBWriteException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "Failed to write data to InfluxDB."
    default_code = "influxdb_write_error"
