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
    maximumDurationInSeconds = 0

    def init_additional_information(self):
        self.maximumDurationInSeconds = self.controllable_action.maximumDurationSeconds or 0
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.http_endpoint = additional_information['http']

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='baa6ef9a-58dc-4e28-b429-d525dfef0941',
            name='Shelly Plug S (HTTP)',
            description="Turns a Shelly Plug S via HTTP calls on and off. MaximumDurationInSeconds adds a delay (optional) to reset the command after the specified time.",
            action_values=['On', 'Off'],
            fields=[
                FieldDescription(
                    id='http',
                    name='Http endpoint;HTTP Endpunkt',
                    description="HTTP endpoint of the Shelly plug.",
                    type=FieldType.STRING,
                    rules=[
                        ValidHttpEndpointRule(),
                    ]
                )
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

            if self.maximumDurationInSeconds > 0:
                params["timer"] = self.maximumDurationInSeconds

            # Send HTTP request
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                logger.info(f"Successfully sent '{action_value}' command to Shelly plug with delay={self.maximumDurationInSeconds}s.")
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
    maximumDurationInSeconds = 0

    def init_additional_information(self):
        self.maximumDurationInSeconds = self.controllable_action.maximumDurationSeconds or 0
        info = json.loads(self.controllable_action.additionalInformation)
        self.mqtt_broker = info['mqtt-broker']
        self.mqtt_port = info.get('mqtt-port', 1883)
        self.mqtt_username = info.get('mqtt-username')
        self.mqtt_password = info.get('mqtt-password')
        self.mqtt_topic = info['mqtt-topic']  # e.g., "shellies/shellyplug-s-1234/relay/0/command"

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='d821e939-3f67-4ac9-bb3c-274ac0a2056e',
            name='Shelly Plug S (MQTT)',
            description="Turns a Shelly Plug S via MQTT communication on and off. MaximumDurationInSeconds adds a delay (optional) to reset the command after the specified time.;Steuert einen Shelly Plug S via MQTT. MaximumDurationInSeconds kann optional genutzt werden um den Befehl nach angegebener Zeit zurückzusetzen.",
            action_values=['On', 'Off'],
            fields=[
                FieldDescription(
                    id='mqtt-broker',
                    name='MQTT broker;MQTT Vermittler',
                    description="MQTT broker address. Example: '192.168.1.100';MQTT Verteiler Adresse. Beispiel: '192.168.1.100'",
                    type=FieldType.STRING,
                    rules=[],
                ),
                FieldDescription(
                    id='mqtt-port',
                    name='MQTT port;MQTT Port',
                    description="Optionally specify a custom MQTT broker port.;Definiere optional einen eigenen MQTT Port.",
                    type=FieldType.INTEGER,
                    rules=[],
                    defaultValue=1883
                ),
                FieldDescription(
                    id='mqtt-username',
                    name='MQTT username;MQTT Nutzername',
                    description="MQTT broker username.;MQTT Verteiler Nutzername.",
                    type=FieldType.STRING,
                    rules=[]),
                FieldDescription(
                    id='mqtt-password',
                    name='MQTT password;MQTT Passwort',
                    description="MQTT broker password.;MQTT Verteiler Passwort.",
                    type=FieldType.STRING,
                    rules=[]),
                FieldDescription(
                    id='mqtt-topic',
                    name='MQTT topic;MQTT Thema',
                    description="MQTT topic to send the command to. Example: 'shellies/shellyplug-s-1234/relay/0/command';MQTT Thema an den der Befehl gesendet wird. Beispiel: 'shellies/shellyplug-s-1234/relay/0/command'",
                    type=FieldType.STRING,
                    rules=[]),
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

            if self.maximumDurationInSeconds > 0:
                logger.info(f"Delaying {self.maximumDurationInSeconds} seconds before sending 'off' command.")
                asyncio.run(self.delayed_off(self.maximumDurationInSeconds))

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