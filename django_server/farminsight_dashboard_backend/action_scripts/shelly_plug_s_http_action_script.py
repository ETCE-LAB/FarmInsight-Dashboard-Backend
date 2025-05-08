import json
import requests
import asyncio

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


logger = get_logger()

class ShellyPlugHttpActionScript(TypedSensor):
    http_endpoint = None

    def init_additional_information(self):
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.http_endpoint = additional_information['http']

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='baa6ef9a-58dc-4e28-b429-d525dfef0941',
            name='Shelly Plug S',
            fields=[
                FieldDescription(
                    name='http',
                    type=FieldType.STRING,
                    rules=[
                        ValidHttpEndpointRule(),
                    ]
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
            try:
                action = json.loads(action_value)
                value = action.get("value", "").strip().lower()
                delay = action.get("delay", 0)
            except (json.JSONDecodeError, TypeError):
                value = str(action_value).strip().lower()
                delay = 0

            if value not in ["on", "off"]:
                logger.error(f"Invalid action value: {value}. Expected 'on' or 'off'.")
                return

            # Build URL
            url = f"http://{self.http_endpoint}/relay/0"
            params = {"turn": value}

            if delay > 0:
                params["timer"] = delay

            # Send HTTP request
            response = requests.get(url, params=params, timeout=5)

            if response.status_code == 200:
                logger.info(f"Successfully sent '{value}' command to Shelly plug with delay={delay}s.")
            else:
                logger.error(f"Failed to control Shelly plug. Status code: {response.status_code}")

        except Exception as e:
            logger.error(f"Exception during Shelly smart plug control: {e}")

    def run(self, action_value):
        try:
            asyncio.run(self.control_smart_plug(action_value=str(action_value).strip().lower()))
        except Exception as e:
            logger.error(f"Exception during smart plug control: {e}")

