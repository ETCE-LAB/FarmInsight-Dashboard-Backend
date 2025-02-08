import json

from channels.generic.websocket import AsyncWebsocketConsumer

from farminsight_dashboard_backend.services.auth_services import check_single_use_token


class SensorUpdatesConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['sensor_id']
        self.room_group_name = f'sensor_updates_{self.room_name}'

        qry_string = str(self.scope["query_string"])
        if 'token' in qry_string:
            token = qry_string.split('=')[1][:-1]
            if await check_single_use_token(token):
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def sensor_measurement(self, event):
        measurement = event['measurement']
        await self.send(text_data=json.dumps({'measurement': measurement}))
