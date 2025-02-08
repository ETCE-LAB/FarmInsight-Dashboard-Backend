from datetime import timedelta

import requests
from channels.db import database_sync_to_async
from decouple import config
from django.utils import timezone

from farminsight_dashboard_backend.models import Sensor, SingleUseToken
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


def valid_api_key_for_sensor(api_key: str, sensor_id: str) -> bool:
    sensor = Sensor.objects.get(id=sensor_id)
    if sensor.FPF.apiKeyValidUntil is None:
        return sensor.FPF.apiKey == api_key
    return sensor.FPF.apiKey == api_key and sensor.FPF.apiKeyValidUntil > timezone.now()


def create_single_use_token() -> str:
    token = generate_random_token(length=64)
    SingleUseToken.objects.create(
        token=token,
        valid_until=timezone.now() + timedelta(minutes=1),
    )

    return token


@database_sync_to_async
def check_single_use_token(token_: str):
    SingleUseToken.objects.filter(valid_until__lt=timezone.now()).delete()

    token = SingleUseToken.objects.filter(token=token_).first()
    if token is None:
        return False

    token.delete()
    return True