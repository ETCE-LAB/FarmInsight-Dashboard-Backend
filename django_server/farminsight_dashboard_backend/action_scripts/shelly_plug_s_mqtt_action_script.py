import json
import asyncio
import paho.mqtt.publish as publish
from farminsight_dashboard_backend.utils import get_logger


from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor

logger = get_logger()

class ShellyPlugSMQTTActionScript(TypedSensor):
    mqtt_broker_host = None
    mqtt_broker_port = 1883
    device_id = None

    def init_additional_information(self):
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.mqtt_broker_host = additional_information['MQTT Broker Host']
        self.device_id = additional_information['Device ID']
        self.mqtt_broker_port = int(additional_information.get('MQTT Broker Port', 1883))  # Optional, default 1883

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='96e354e3-9064-4a6f-9fd4-fe378eed23f5',
            name='Shelly Plug S MQTT',
            fields=[
                FieldDescription(
                    name='MQTT Broker Host',
                    type=FieldType.STRING,
                    rules=[]
                ),
                FieldDescription(
                    name='MQTT Broker Port',
                    type=FieldType.NUMBER,
                    rules=[]
                ),
                FieldDescription(
                    name='Device ID',
                    type=FieldType.STRING,
                    rules=[]
                ),
            ]
        )

    async def control_smart_plug(self, action_value):
        topic = f"shellies/shellyplug-s-{self.device_id}/relay/0/command"
        action_value = str(action_value).strip().lower()

        if action_value not in ['on', 'off']:
            logger.error(f"Invalid action value: {action_value}. Expected 'on' or 'off'.")
            return

        try:
            publish.single(topic, payload=action_value, hostname=self.mqtt_broker_host, port=self.mqtt_broker_port)
            logger.info(f"Published '{action_value}' to {topic}")
        except Exception as e:
            logger.error(f"Failed to publish MQTT message: {e}")

    def run(self, action_value):
        try:
            asyncio.run(self.control_smart_plug(action_value))
        except Exception as e:
            logger.error(f"Exception during Shelly smart plug control: {e}")
