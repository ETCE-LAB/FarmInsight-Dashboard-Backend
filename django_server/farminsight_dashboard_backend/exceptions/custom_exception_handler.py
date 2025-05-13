from django.db import IntegrityError

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException

from farminsight_dashboard_backend.utils import get_logger


logger = get_logger()


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    resource_id = None
    if 'sensor_id' in context['kwargs']:
        resource_id = context['kwargs']['sensor_id']
    elif 'camera_id' in context['kwargs']:
        resource_id = context['kwargs']['camera_id']
    elif 'fpf_id' in context['kwargs']:
        resource_id = context['kwargs']['fpf_id']
    elif 'organization_id' in context['kwargs']:
        resource_id = context['kwargs']['organization_id']
    elif 'resource_id' in context['kwargs']:
        resource_id = context['kwargs']['resource_id']

    if isinstance(exc, IntegrityError):
        logger.error("A database integrity error occurred. " + str(exc), extra={'resource_id': resource_id})
        return Response(
            {"error": "A database integrity error occurred.", "details": str(exc)},
            status=status.HTTP_400_BAD_REQUEST
        )

    if isinstance(exc, APIException):
        logger.error(str(exc.default_detail) + str(exc.detail), extra={'resource_id': resource_id})
        return Response(
            {"error": exc.default_detail, "details": exc.detail},
            status=exc.status_code
        )

    logger.error("An unexpected error occurred. " + str(exc), extra={'resource_id': resource_id})
    if response is None:
        return Response(
            {"error": "An unexpected error occurred.", "details": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
