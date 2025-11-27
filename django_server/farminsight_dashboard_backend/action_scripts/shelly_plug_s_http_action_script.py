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
        logger.info("Initializing Shelly Plug S (HTTP) action script.")
        self.maximumDurationInSeconds = self.controllable_action.maximumDurationSeconds or 0
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.http_endpoint = additional_information['http']
        logger.info(f"Shelly Plug S (HTTP) initialized for endpoint: {self.http_endpoint}")

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='baa6ef9a-58dc-4e28-b429-d525dfef0941',
            name='Shelly Plug S (HTTP)',
            description=("Turns a Shelly Plug S via HTTP calls on and off. Maximum duration in seconds adds an optional delay to reset the command after the specified time."
                         ";Steuert einen Shelly Plug S über HTTP. Maximale Dauer in Sekunden fügt eine optionale Wartezeit hinzu die das Kommando nach der angegebenen Dauer umkehrt."),
            action_values=['On', 'Off'],
            fields=[
                FieldDescription(
                    id='http',
                    name='Http endpoint;HTTP Endpunkt',
                    description="HTTP endpoint of the Shelly plug.;HTTP Endpunkt des Shelly Steckers.",
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
            logger.info(f"Controlling Shelly plug at {self.http_endpoint} with action: {action_value}")
            if action_value not in ["on", "off"]:
                logger.error(f"Invalid action value: {action_value}. Expected 'on' or 'off'.", extra={'resource_id': self.controllable_action.id})
                return

            # Build URL
            url = f"http://{self.http_endpoint}/relay/0"
            params = {"turn": action_value}

            if self.maximumDurationInSeconds > 0:
                params["timer"] = self.maximumDurationInSeconds
                logger.info(f"Action will be reversed after {self.maximumDurationInSeconds} seconds.")

            # Send HTTP request
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                logger.info(f"Successfully sent '{action_value}' command to Shelly plug at {self.http_endpoint}.")
            else:
                logger.error(f"Failed to control Shelly plug at {self.http_endpoint}. Status: {response.status_code}, Response: {response.text}", extra={'resource_id': self.controllable_action.id})

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed for Shelly plug at {self.http_endpoint}: {e}", extra={'resource_id': self.controllable_action.id})
        except Exception as e:
            logger.error(f"An unexpected error occurred during Shelly smart plug control: {e}", extra={'resource_id': self.controllable_action.id})

    def run(self, action_value):
        try:
            logger.info(f"Running Shelly Plug HTTP action with value: {action_value}")
            asyncio.run(self.control_smart_plug(action_value=str(action_value).strip().lower()))
        except Exception as e:
            logger.error(f"Exception during smart plug control execution: {e}", extra={'resource_id': self.controllable_action.id})


class ShellyPlugMqttActionScript(TypedSensor):
    mqtt_broker = None
    mqtt_port = 1883
    mqtt_username = None
    mqtt_password = None
    mqtt_topic = None
    maximumDurationInSeconds = 0

    def init_additional_information(self):
        logger.info("Initializing Shelly Plug S (MQTT) action script.")
        self.maximumDurationInSeconds = self.controllable_action.maximumDurationSeconds or 0
        info = json.loads(self.controllable_action.additionalInformation)
        self.mqtt_broker = info['mqtt-broker']
        self.mqtt_port = info.get('mqtt-port', 1883)
        self.mqtt_username = info.get('mqtt-username')
        self.mqtt_password = info.get('mqtt-password')
        self.mqtt_topic = info['mqtt-topic']
        logger.info(f"Shelly Plug S (MQTT) initialized for broker: {self.mqtt_broker}, topic: {self.mqtt_topic}")

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='d821e939-3f67-4ac9-bb3c-274ac0a2056e',
            name='Shelly Plug S (MQTT)',
            description=("Turns a Shelly Plug S via MQTT communication on and off. MaximumDurationInSeconds adds a delay (optional) to reset the command after the specified time."
                         ";Steuert einen Shelly Plug S über MQTT. Maximale Dauer in Sekunden fügt eine optionale Wartezeit hinzu die das Kommando nach der angegebenen Dauer umkehrt."),
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
            logger.info(f"Sending MQTT command. Topic: '{topic}', Payload: '{payload}'")
            client = mqtt.Client()
            if self.mqtt_username and self.mqtt_password:
                client.username_pw_set(self.mqtt_username, self.mqtt_password)

            client.connect(self.mqtt_broker, self.mqtt_port, 60)
            client.loop_start()
            result = client.publish(topic, payload)
            result.wait_for_publish()
            client.loop_stop()
            client.disconnect()

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Successfully sent '{payload}' to topic '{topic}'")
            else:
                logger.error(f"Failed to publish MQTT message to topic '{topic}'. Return code: {result.rc}", extra={'resource_id': self.controllable_action.id})
                raise RuntimeError(f"Failed to publish message. MQTT return code: {result.rc}")
        except Exception as e:
            logger.error(f"Exception during MQTT communication: {e}", extra={'resource_id': self.controllable_action.id})
            raise RuntimeError(f"Exception during MQTT communication: {e}")

    def control_smart_plug(self, action_value):
        try:
            logger.info(f"Controlling Shelly plug via MQTT with action: {action_value}")
            if action_value not in ["on", "off"]:
                logger.error(f"Invalid action value: {action_value}. Expected 'on' or 'off'.")
                raise ValueError(f"Invalid action value: {action_value}. Expected 'on' or 'off'.")

            self.send_mqtt_command(self.mqtt_topic, action_value)

            if self.maximumDurationInSeconds > 0:
                opposite_action = "off" if action_value == "on" else "on"
                logger.info(f"Action will be reversed to '{opposite_action}' after {self.maximumDurationInSeconds} seconds.")
                asyncio.run(self.delayed_action(self.maximumDurationInSeconds, opposite_action))

        except Exception as e:
            logger.error(f"Exception during Shelly smart plug control: {e}", extra={'resource_id': self.controllable_action.id})
            raise RuntimeError(f"Exception during Shelly smart plug control: {e}") from e

    async def delayed_action(self, delay_seconds: int, action: str):
        await asyncio.sleep(delay_seconds)
        logger.info(f"Executing delayed action: '{action}'")
        self.send_mqtt_command(self.mqtt_topic, action)

    def run(self, action_value):
        try:
            logger.info(f"Running Shelly Plug MQTT action with value: {action_value}")
            self.control_smart_plug(action_value=str(action_value).strip().lower())
        except Exception as e:
            logger.error(f"Exception during smart plug control execution: {e}", extra={'resource_id': self.controllable_action.id})
            raise RuntimeError(f"Exception during smart plug control: {e}")
