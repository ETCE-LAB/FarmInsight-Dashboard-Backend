import uuid
from json import JSONDecodeError
import requests
from django.core.files import File
from requests import RequestException
from farminsight_dashboard_backend.models import Image



def send_request_to_fpf(fpf_id, method, endpoint, data=None, params=None):
    """
    Send an HTTP request and return the JSON response.
    :param endpoint: API endpoint
    :param fpf_id:
    :param method: 'get', 'post', or 'put'
    :param data: Data to send in the case of post/put
    :param params: Parameters to append to the URL
    :return: JSON response data
    """
    from farminsight_dashboard_backend.services import get_fpf_by_id, get_auth_token
    fpf = get_fpf_by_id(fpf_id)
    url = f"{build_fpf_url(fpf.sensorServiceIp, endpoint)}"
    #token = get_auth_token()
    token = 'eyJhbGciOiJSUzI1NiIsImtpZCI6IjlFREE4MDY3Qzk0ODFBRkU4QjY1QjNGQThBMjZCRTY3IiwidHlwIjoiYXQrand0In0.eyJpc3MiOiJodHRwczovL2RldmVsb3BtZW50LWlzc2UtaWRlbnRpdHlzZXJ2ZXIuYXp1cmV3ZWJzaXRlcy5uZXQiLCJuYmYiOjE3MzQwODA1NzEsImlhdCI6MTczNDA4MDU3MSwiZXhwIjoxNzM0MDg0MTcxLCJhdWQiOiJodHRwczovL2RldmVsb3BtZW50LWlzc2UtaWRlbnRpdHlzZXJ2ZXIuYXp1cmV3ZWJzaXRlcy5uZXQvcmVzb3VyY2VzIiwic2NvcGUiOlsib3BlbmlkIl0sImFtciI6WyJwd2QiXSwiY2xpZW50X2lkIjoiaW50ZXJhY3RpdmUiLCJzdWIiOiIwOWNmOWM2Zi1mYTU2LTRmYjItYjg1Ni1hYTM1OGYzNmNiNjAiLCJhdXRoX3RpbWUiOjE3MzQwNzgyMzcsImlkcCI6ImxvY2FsIiwiZW1haWwiOiJtYXIucGV0ZXJAb3N0ZmFsaWEuZGUiLCJuYW1lIjoibWFyLnBldGVyQG9zdGZhbGlhLmRlIiwiaWQiOiIwOWNmOWM2Zi1mYTU2LTRmYjItYjg1Ni1hYTM1OGYzNmNiNjAiLCJzaWQiOiIyRjk4QkU4RjI0NkNFOUQ2MTI3MTJBMEU5MkI5MzczNCIsImp0aSI6IjM5RTI3QTk1MzVGNDRCNjk0RDdBRUU2ODc4ODZEMjc2In0.Ai4Ccz4R2krFh8ew2F-Fc9ruNyVOqSi0YbdDUIC6nRnN_YeVvsLjviDC_HfD0-n1mgy91ODSlUxBYW0DFevAwaksk6t2USQZfy9lH8AVdzI2pSpfbUqXIWhi7u9JQ16T6_t7i5QzhARgbrfLtk-4j45uijfqNDnJ1_RmLIkDGhHRjGoXJh9neo7I9lFvioSZ-MP3gYOD8uknQGg-WIliqTsiVBmxy-YsBwq_qKG1qotWzavvH76T1jkEzJAom2GrxYfZViV6SFfq_dYqkUWNXylgP4N34ZdSP8Q_yZk2n-cPgqKy4S3MVQwpiv5Nd0xr88IVE9MBBq6TggptD5xG1w'
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.request(method, url, json=data, params=params, headers=headers, timeout=10)
        #response = requests.request(method, url, json=data, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    except JSONDecodeError as e:
        return None
    except RequestException as e:
        raise Exception(f"Cannot reach the FPF service at {url}: {str(e)}")

    except ValueError:
        raise Exception("Invalid JSON response from the FPF service.")

def fetch_camera_snapshot(camera_id, snapshot_url):
    """
    Fetch a snapshot from the given snapshot URL of the camera and store it as a jpg file.
    :param camera_id:
    :param snapshot_url:
    :return:
    """
    try:
        response = requests.get(snapshot_url, stream=True)
        if response.status_code == 200:

            filename = f"{str(uuid.uuid4())}.jpg"
            Image.objects.create(
                camera_id=camera_id,
                image=File(response.raw, name=filename)
            )

            return filename

        else:
            raise ValueError(f"Failed to fetch snapshot. HTTP {response.status_code}")
    except Exception as e:
        print(f"Error fetching snapshot for Camera {camera_id}: {e}")

def build_fpf_url(fpf_address, endpoint):
    """
    Build a correct URL based on the FPF config
    :param endpoint:
    :param fpf_address:
    :return:
    """
    if fpf_address.startswith(('http://', 'https://')):
        if endpoint.startswith('/'):
            return f"{fpf_address}{endpoint}"
        return f"{fpf_address}/{endpoint}"
    if endpoint.startswith('/'):
        return f"http://{fpf_address}{endpoint}"
    return f"http://{fpf_address}/{endpoint}"
