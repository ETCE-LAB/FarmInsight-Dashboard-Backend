import json
import requests
import asyncio

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


logger = get_logger()

class PostHttpActionScript(TypedSensor):
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
        Controls the smart plug by turning it on or off.
        :param action_value:
        :return:
        """
        if action_value not in ['on', 'off']:
            logger.error(f"Invalid action value: {action_value}. Excpected 'on' or 'off'.")
            return

        on_value = action_value == 'on'

        url = f"http://{self.http_endpoint}/rpc/Switch.Set"
        payload = {"id": 0, "on": on_value}

        try:
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info(f"Successfully sent {action_value} command to Shelly plug.")
            else:
                logger.error(f"Failed to send {action_value} command to Shelly plug.")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send {action_value} command to Shelly plug.")


    def run(self, action_value):
        try:
            asyncio.run(self.control_smart_plug(action_value=str(action_value).strip().lower()))
        except Exception as e:
            logger.error(f"Exception during smart plug control: {e}")

