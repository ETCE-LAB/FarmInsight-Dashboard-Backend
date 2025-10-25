from datetime import timedelta

import requests
from channels.db import database_sync_to_async
from decouple import config
from django.utils import timezone

from farminsight_dashboard_backend.models import Sensor, FPF, SingleUseToken, Userprofile
from farminsight_dashboard_backend.utils import generate_random_token


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
    response = requests.post(url, data=data, headers=headers)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception(f"Failed to obtain token: {response.status_code}, {response.text}")


def valid_api_key_for_fpf(api_key: str, fpf_id: str) -> bool:
    fpf = FPF.objects.get(id=fpf_id)
    if fpf.apiKeyValidUntil is None:
        return fpf.apiKey == api_key
    return fpf.apiKey == api_key and fpf.apiKeyValidUntil > timezone.now()


def valid_api_key_for_sensor(api_key: str, sensor_id: str) -> bool:
    sensor = Sensor.objects.get(id=sensor_id)
    if sensor.FPF.apiKeyValidUntil is None:
        return sensor.FPF.apiKey == api_key
    return sensor.FPF.apiKey == api_key and sensor.FPF.apiKeyValidUntil > timezone.now()


def create_single_use_token(user: Userprofile, duration_minutes: int = 1) -> str:
    token = generate_random_token(length=64)
    SingleUseToken.objects.create(
        token=token,
        valid_until=timezone.now() + timedelta(minutes=duration_minutes),
        user=user,
    )

    return token


def get_user_from_single_use_token(token_: str, delete_token: bool = True) -> Userprofile|None:
    SingleUseToken.objects.filter(valid_until__lt=timezone.now()).delete()

    token = SingleUseToken.objects.filter(token=token_).first()
    if token is None:
        return None

    user = token.user
    if delete_token:
        token.delete()
    return user