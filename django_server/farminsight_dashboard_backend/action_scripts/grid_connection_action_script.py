import json
import requests
import asyncio

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


logger = get_logger()


class GridConnectionActionScript(TypedSensor):
    """
    Action script for controlling grid connection.
    Supports connect/disconnect operations via HTTP endpoint.
    """
    http_endpoint = None
    maximumDurationInSeconds = 0

    def init_additional_information(self):
        self.maximumDurationInSeconds = self.controllable_action.maximumDurationSeconds or 0
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.http_endpoint = additional_information.get('http')

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='e8a7f3c1-9b2d-4e5f-a6c8-1d2e3f4a5b6c',
            name='Grid Connection Controller',
            description=(
                "Controls grid connection for energy management. Connects or disconnects the facility from the power grid based on battery levels and energy requirements."
                ";Steuert die Netzverbindung für das Energiemanagement. Verbindet oder trennt die Anlage vom Stromnetz basierend auf Batteriestand und Energiebedarf."
            ),
            action_values=['Connect', 'Disconnect'],
            fields=[
                FieldDescription(
                    id='http',
                    name='HTTP endpoint;HTTP Endpunkt',
                    description="HTTP endpoint of the grid connection controller (e.g., smart relay or transfer switch).;HTTP Endpunkt des Netzverbindungscontrollers (z.B. Smart-Relais oder Umschalter).",
                    type=FieldType.STRING,
                    rules=[
                        ValidHttpEndpointRule(),
                    ]
                )
            ]
        )

    async def control_grid_connection(self, action_value: str):
        """
        Controls the grid connection via HTTP.
        :param action_value: 'connect' or 'disconnect'
        """
        try:
            action_lower = action_value.lower().strip()

            if action_lower not in ["connect", "disconnect"]:
                logger.error(
                    f"Invalid action value: {action_value}. Expected 'connect' or 'disconnect'.",
                    extra={'resource_id': self.controllable_action.id}
                )
                return

            # Map action to relay state
            # connect = turn relay on (grid connected)
            # disconnect = turn relay off (grid disconnected)
            relay_state = "on" if action_lower == "connect" else "off"

            # Build URL - compatible with common smart relay/switch APIs
            url = f"http://{self.http_endpoint}/relay/0"
            params = {"turn": relay_state}

            if self.maximumDurationInSeconds > 0:
                params["timer"] = self.maximumDurationInSeconds

            # Send HTTP request
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                logger.info(
                    f"Successfully sent '{action_lower}' command to grid controller.",
                    extra={'resource_id': self.controllable_action.id}
                )

                # Log the grid state change
                from farminsight_dashboard_backend.services.log_message_services import write_log_message
                write_log_message(
                    resource_id=str(self.controllable_action.id),
                    resource_type="controllable_action",
                    message=f"Grid {'connected' if action_lower == 'connect' else 'disconnected'} successfully"
                )
            else:
                logger.error(
                    f"Failed to control grid connection. Status code: {response.status_code}",
                    extra={'resource_id': self.controllable_action.id}
                )

        except requests.exceptions.Timeout:
            logger.error(
                "Timeout while attempting to control grid connection.",
                extra={'resource_id': self.controllable_action.id}
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Connection error while controlling grid: {e}",
                extra={'resource_id': self.controllable_action.id}
            )
        except Exception as e:
            logger.error(
                f"Exception during grid connection control: {e}",
                extra={'resource_id': self.controllable_action.id}
            )

    def run(self, action_value):
        """
        Execute the grid connection action
        :param action_value: 'Connect' or 'Disconnect'
        """
        try:
            asyncio.run(self.control_grid_connection(action_value=str(action_value).strip().lower()))
        except Exception as e:
            logger.error(
                f"Exception during grid connection control: {e}",
                extra={'resource_id': self.controllable_action.id}
            )


class GridConnectionMqttActionScript(TypedSensor):
    """
    MQTT-based grid connection controller for systems using MQTT protocol.
    """
    mqtt_topic = None
    mqtt_broker = None
    mqtt_port = 1883

    def init_additional_information(self):
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.mqtt_topic = additional_information.get('mqtt_topic')
        self.mqtt_broker = additional_information.get('mqtt_broker')
        self.mqtt_port = additional_information.get('mqtt_port', 1883)

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='f9b8e4d2-0c3e-5f60-b7d9-2e3f4a5b6c7d',
            name='Grid Connection Controller (MQTT)',
            description=(
                "Controls grid connection via MQTT protocol. For systems using MQTT-based smart switches or relays."
                ";Steuert die Netzverbindung über MQTT-Protokoll. Für Systeme mit MQTT-basierten Smart-Schaltern oder Relais."
            ),
            action_values=['Connect', 'Disconnect'],
            fields=[
                FieldDescription(
                    id='mqtt_broker',
                    name='MQTT Broker;MQTT Broker',
                    description="MQTT broker address.;MQTT Broker-Adresse.",
                    type=FieldType.STRING,
                    rules=[]
                ),
                FieldDescription(
                    id='mqtt_port',
                    name='MQTT Port;MQTT Port',
                    description="MQTT broker port (default: 1883).;MQTT Broker-Port (Standard: 1883).",
                    type=FieldType.INTEGER,
                    rules=[]
                ),
                FieldDescription(
                    id='mqtt_topic',
                    name='MQTT Topic;MQTT Topic',
                    description="MQTT topic for grid control commands.;MQTT Topic für Netzsteuerungsbefehle.",
                    type=FieldType.STRING,
                    rules=[]
                )
            ]
        )

    def run(self, action_value):
        """
        Execute the grid connection action via MQTT
        :param action_value: 'Connect' or 'Disconnect'
        """
        try:
            import paho.mqtt.client as mqtt

            action_lower = action_value.lower().strip()
            payload = "ON" if action_lower == "connect" else "OFF"

            client = mqtt.Client()
            client.connect(self.mqtt_broker, self.mqtt_port, 60)
            client.publish(self.mqtt_topic, payload)
            client.disconnect()

            logger.info(
                f"Successfully sent '{action_lower}' command via MQTT to {self.mqtt_topic}",
                extra={'resource_id': self.controllable_action.id}
            )

        except Exception as e:
            logger.error(
                f"Exception during MQTT grid connection control: {e}",
                extra={'resource_id': self.controllable_action.id}
            )

