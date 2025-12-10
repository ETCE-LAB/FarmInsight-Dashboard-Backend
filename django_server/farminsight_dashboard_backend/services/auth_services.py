import logging
from datetime import timedelta

import requests
from channels.db import database_sync_to_async
from decouple import config
from django.utils import timezone

from farminsight_dashboard_backend.models import Sensor, FPF, SingleUseToken, Userprofile
from farminsight_dashboard_backend.utils import generate_random_token

logger = logging.getLogger(__name__)


def get_auth_token():
    """
    Fetch the authentication token from the external auth service.
    """
    url = config('AUTH_SERVICE_URL')
    data = {
        "grant_type": "client_credentials",
        "client_id": config('CLIENT_ID'),
        "client_secret": config('CLIENT_SECRET'),
        "scope": "identity" # openid profile email
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    logger.info("Requesting new auth token from external service.")
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        logger.info("Successfully obtained new auth token.")
        return response.json().get("access_token")
    else:
        logger.error(f"Failed to obtain auth token. Status: {response.status_code}, Response: {response.text}")
        raise Exception(f"Failed to obtain token: {response.status_code}, {response.text}")


def valid_api_key_for_fpf(api_key: str, fpf_id: str) -> bool:
    fpf = FPF.objects.get(id=fpf_id)
    logger.debug(f"Validating API key for FPF: '{fpf.name}'.")
    if fpf.apiKeyValidUntil is None:
        is_valid = fpf.apiKey == api_key
    else:
        is_valid = fpf.apiKey == api_key and fpf.apiKeyValidUntil > timezone.now()

    if is_valid:
        logger.info(f"API key validation successful for FPF: '{fpf.name}'.")
    else:
        logger.warning(f"API key validation failed for FPF: '{fpf.name}'.")
    return is_valid


def valid_api_key_for_sensor(api_key: str, sensor_id: str) -> bool:
    sensor = Sensor.objects.get(id=sensor_id)
    logger.debug(f"Validating API key for sensor: '{sensor.name}'.")
    if sensor.FPF.apiKeyValidUntil is None:
        is_valid = sensor.FPF.apiKey == api_key
    else:
        is_valid = sensor.FPF.apiKey == api_key and sensor.FPF.apiKeyValidUntil > timezone.now()

    if is_valid:
        logger.info(f"API key validation successful for sensor: '{sensor.name}'.")
    else:
        logger.warning(f"API key validation failed for sensor: '{sensor.name}'.")
    return is_valid


def create_single_use_token(user: Userprofile, duration_minutes: int = 1) -> str:
    token = generate_random_token(length=64)
    SingleUseToken.objects.create(
        token=token,
        valid_until=timezone.now() + timedelta(minutes=duration_minutes),
        user=user,
    )
    logger.info(f"Created single-use token for user: '{user.username}' valid for {duration_minutes} minutes.")
    return token


def get_user_from_single_use_token(token_: str, delete_token: bool = True) -> Userprofile|None:
    logger.debug("Attempting to validate and retrieve user from single-use token.")
    SingleUseToken.objects.filter(valid_until__lt=timezone.now()).delete()

    token = SingleUseToken.objects.filter(token=token_).first()
    if token is None:
        logger.warning("Attempted to use an invalid or expired single-use token.")
        return None

    user = token.user
    if delete_token:
        token.delete()
        logger.info(f"Single-use token for user '{user.username}' has been used and deleted.")
    return user
