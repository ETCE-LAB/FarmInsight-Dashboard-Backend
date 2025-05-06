import json

from channels.generic.websocket import AsyncWebsocketConsumer

from farminsight_dashboard_backend.models import LogMessage
from farminsight_dashboard_backend.services import sensor_exists_async

class SensorUpdatesConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_group_name = None
        self.room_name = None

    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['sensor_id']
            self.room_group_name = f'sensor_updates_{self.room_name}'

            if await sensor_exists_async(self.room_name):
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.accept()
            else:
                await self.close()
        except Exception as e:
            await LogMessage.objects.acreate(
                message=f"WEBSOCKET EXCEPTION: {e}",
                logLevel='ERROR',
            )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def sensor_measurement(self, event):
        measurement = event['measurement']
        await self.send(text_data=json.dumps({'measurement': measurement}))
