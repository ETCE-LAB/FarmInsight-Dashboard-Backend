import json
import requests
import asyncio
import paho.mqtt.client as mqtt

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


logger = get_logger()

class ShellyPlugHttpActionScript(TypedSensor):
    http_endpoint = None
    delay = 0

    def init_additional_information(self):
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.http_endpoint = additional_information['http']
        self.delay = additional_information.get('delay', 0)

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='baa6ef9a-58dc-4e28-b429-d525dfef0941',
            name='Shelly Plug S (HTTP)',
            fields=[
                FieldDescription(
                    name='Http',
                    description="HTTP endpoint of the Shelly plug.",
                    type=FieldType.STRING,
                    rules=[
                        ValidHttpEndpointRule(),
                    ]
                ),
                FieldDescription(
                    name='Delay',
                    description="Optional delay in seconds before turning off the plug after turning it on.",
                    type=FieldType.INTEGER,
                    rules=[],
                    defaultValue=0
                ),
            ]
        )

    async def control_smart_plug(self, action_value):
        """
        Controls the Shelly plug via HTTP.
        Supports:
        - Plain string: "on" / "off"
        - JSON string: {"value": "on", "delay": 1800}
        """
        try:
            # Try parsing JSON input

            if action_value not in ["on", "off"]:
                logger.error(f"Invalid action value: {action_value}. Expected 'on' or 'off'.")
                return

            # Build URL
            url = f"http://{self.http_endpoint}/relay/0"
            params = {"turn": action_value}

            if self.delay > 0:
                params["timer"] = self.delay

            # Send HTTP request
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                logger.info(f"Successfully sent '{action_value}' command to Shelly plug with delay={self.delay}s.")
            else:
                logger.error(f"Failed to control Shelly plug. Status code: {response.status_code}")

        except Exception as e:
            logger.error(f"Exception during Shelly smart plug control: {e}")

    def run(self, action_value):
        try:
            asyncio.run(self.control_smart_plug(action_value=str(action_value).strip().lower()))
        except Exception as e:
            logger.error(f"Exception during smart plug control: {e}")


class ShellyPlugMqttActionScript(TypedSensor):
    mqtt_broker = None
    mqtt_port = 1883
    mqtt_username = None
    mqtt_password = None
    mqtt_topic = None
    delay = 0

    def init_additional_information(self):
        info = json.loads(self.controllable_action.additionalInformation)
        self.mqtt_broker = info['mqtt_broker']
        self.mqtt_port = info.get('mqtt_port', 1883)
        self.mqtt_username = info.get('mqtt_username')
        self.mqtt_password = info.get('mqtt_password')
        self.mqtt_topic = info['mqtt_topic']  # e.g., "shellies/shellyplug-s-1234/relay/0/command"
        self.delay = info.get('delay', 0)

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='d821e939-3f67-4ac9-bb3c-274ac0a2056e',
            name='Shelly Plug S (MQTT)',
            fields=[
                FieldDescription(
                    name='MQTT broker',
                    description="MQTT broker address. Example: '192.168.1.100'",
                    type=FieldType.STRING,
                    rules=[],
                ),
                FieldDescription(
                    name='MQTT port',
                    description="Optionally specify a custom MQTT broker port.",
                    type=FieldType.INTEGER,
                    rules=[],
                    defaultValue=1883
                ),
                FieldDescription(
                    name='MQTT username',
                    description="MQTT broker username.",
                    type=FieldType.STRING,
                    rules=[]),
                FieldDescription(
                    name='MQTT password',
                    description="MQTT broker password.",
                    type=FieldType.STRING,
                    rules=[]),
                FieldDescription(
                    name='MQTT topic',
                    description="MQTT topic to send the command to. Example: 'shellies/shellyplug-s-1234/relay/0/command'",
                    type=FieldType.STRING,
                    rules=[]),
                FieldDescription(
                    name='Delay',
                    description="Delay in seconds before turning off the plug after turning it on.",
                    type=FieldType.INTEGER,
                    rules=[],
                    defaultValue=0
                ),
            ]
        )

    def send_mqtt_command(self, topic: str, payload: str):
        try:
            client = mqtt.Client()
            if self.mqtt_username and self.mqtt_password:
                client.username_pw_set(self.mqtt_username, self.mqtt_password)

            client.connect(self.mqtt_broker, self.mqtt_port, 60)
            client.loop_start()
            logger.debug(f"Publishing to {topic}: {payload}")
            result = client.publish(topic, payload)
            result.wait_for_publish()
            client.loop_stop()
            client.disconnect()

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Successfully sent '{payload}' to topic '{topic}'")
            else:
                logger.error(f"Failed to publish message. MQTT return code: {result.rc}")
        except Exception as e:
            logger.error(f"Exception during MQTT communication: {e}")

    def control_smart_plug(self, action_value):
        try:

            if action_value not in ["on", "off"]:
                logger.error(f"Invalid action value: {action_value}. Expected 'on' or 'off'.")
                return

            self.send_mqtt_command(self.mqtt_topic, action_value)

            if self.delay > 0:
                logger.info(f"Delaying {self.delay} seconds before sending 'off' command.")
                asyncio.run(self.delayed_off(self.delay))

        except Exception as e:
            logger.error(f"Exception during Shelly smart plug control: {e}")

    async def delayed_off(self, delay_seconds: int):
        await asyncio.sleep(delay_seconds)
        self.send_mqtt_command(self.mqtt_topic, "off")

    def run(self, action_value):
        try:
            self.control_smart_plug(action_value=str(action_value).strip().lower())
        except Exception as e:
            logger.error(f"Exception during smart plug control: {e}")