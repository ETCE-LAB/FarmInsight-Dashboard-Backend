import asyncio
import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from farminsight_dashboard_backend.models import LogMessage
from farminsight_dashboard_backend.services import sensor_exists, get_active_camera_by_id
from farminsight_dashboard_backend.services.fpf_streaming_services import websocket_stream
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()

class SensorUpdatesConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_group_name = None
        self.room_name = None

    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['sensor_id']
            self.room_group_name = f'sensor_updates_{self.room_name}'

            if sensor_exists(self.room_name):
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.accept()
            else:
                await self.close()
        except Exception as e:
            await LogMessage.objects.acreate(
                message=f"{e}",
                logLevel='INFO',
            )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def sensor_measurement(self, event):
        measurement = event['measurement']
        await self.send(text_data=json.dumps({'measurement': measurement}))


class CameraLivestreamConsumer(AsyncWebsocketConsumer):
    """
    Integration of  websocket_stream:
    - Stream Task starts when first Client connects
    - Stream Task stops when last Client disconnects
    - Frames are sent to all connected clients via channel_layer.group_send
    """
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_group_name = None
        self.room_name = None

    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['camera_id']
            self.room_group_name = f'camera_livestream_{self.room_name}'
            logger.info(self.room_group_name)

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

            # Get livestream URL from Camera
            try:
                camera = await sync_to_async(get_active_camera_by_id)(self.room_name)
                livestream_url = camera.livestreamUrl
            except Exception as e:
                await LogMessage.objects.acreate(
                    message=f"{e}",
                    logLevel='INFO',
                )
                return

            # Start of streaming task (if not already started)
            await WebsocketStreamingManager.add_client(self.room_name, livestream_url, self.room_group_name)
        except Exception as e:
            await LogMessage.objects.acreate(
                message=f"{e}",
                logLevel='INFO',
            )

    async def disconnect(self, close_code):
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
            await WebsocketStreamingManager.remove_client(self.room_name)
        except Exception as e:
            await LogMessage.objects.acreate(
                message=f"{e}",
                logLevel='INFO',
            )

    async def camera_frame(self, event):
        frame_data = event['frame_data']
        await self.send(text_data=json.dumps({'frame_data': frame_data}))



class WebsocketStreamingManager:
    """
    Static class to manage websocket streaming tasks.:
    - tracks active streaming tasks per camera_id
    - starts a new streaming task when the first client connects
    - stops the streaming task when the last client disconnects
    - uses asyncio.Lock to ensure thread-safe access to the internal state
    """
    _streams: dict = {}
    _lock = asyncio.Lock()

    @classmethod
    async def add_client(cls, camera_id: str, livestream_url: str, group_name: str, max_fps: int = 5):
        async with cls._lock:
            entry = cls._streams.get(camera_id)
            if entry:
                entry['clients'] += 1
                return
            stop_event = asyncio.Event()
            task = asyncio.create_task(websocket_stream(livestream_url, group_name, max_fps=max_fps, stop_event=stop_event))

            # cleanup if task is done
            def _done_callback(t, cid=camera_id):
                try:
                    # entferne Eintrag asynchron
                    asyncio.create_task(cls._cleanup(cid))
                except Exception:
                    pass

            task.add_done_callback(_done_callback)
            cls._streams[camera_id] = {'task': task, 'clients': 1, 'stop_event': stop_event}

    @classmethod
    async def remove_client(cls, camera_id: str):
        async with cls._lock:
            entry = cls._streams.get(camera_id)
            if not entry:
                return
            entry['clients'] -= 1
            if entry['clients'] <= 0:
                # Stop the streaming task
                entry['stop_event'].set()

    @classmethod
    async def _cleanup(cls, camera_id: str):
        async with cls._lock:
            cls._streams.pop(camera_id, None)