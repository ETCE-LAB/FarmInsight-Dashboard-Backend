import json

from channels.generic.websocket import AsyncWebsocketConsumer

from farminsight_dashboard_backend.services import sensor_exists
from farminsight_dashboard_backend.services.auth_services import check_single_use_token


class SensorUpdatesConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.room_group_name = None
        self.room_name = None

    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['sensor_id']
        self.room_group_name = f'sensor_updates_{self.room_name}'

        if sensor_exists(self.room_name):
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def sensor_measurement(self, event):
        measurement = event['measurement']
        await self.send(text_data=json.dumps({'measurement': measurement}))
