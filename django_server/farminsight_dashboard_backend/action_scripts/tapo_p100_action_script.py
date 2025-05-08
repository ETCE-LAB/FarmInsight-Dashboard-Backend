import json
import asyncio

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor
from PyP100 import PyP100  # pip install git+https://github.com/almottier/TapoP100.git@main or via requirements.txt

logger = get_logger()


class TapoP100SmartPlugActionScriptWithDelay(TypedSensor):
    ip_address = None
    tapo_account_email = None
    tapo_account_password = None

    def init_additional_information(self):
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.ip_address = additional_information['IP Address']
        self.tapo_account_email = additional_information['Tapo Account Email']
        self.tapo_account_password = additional_information['Tapo Account Password']

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='dc83813b-1541-4aac-8caa-ba448a6bbdda',
            name='Tapo Smart Plug',
            fields=[
                FieldDescription(
                    name='IP Address',
                    type=FieldType.STRING,
                    rules=[]
                ),
                FieldDescription(
                    name='Tapo Account Email',
                    type=FieldType.STRING,
                    rules=[]
                ),
                FieldDescription(
                    name='Tapo Account Password',
                    type=FieldType.STRING,
                    rules=[]
                )
            ]
        )

    async def control_smart_plug(self, action_value):
        """
            Controls the smart plug by turning it on or off.
            Supports:
            - Plain string: "on" / "off"
            - JSON string: {"value": "on", "delay": 1800}
            """
        try:
            # Try parsing as JSON
            try:
                action = json.loads(action_value)
                value = action.get('value')
                delay = action.get('delay', 0)
            except (json.JSONDecodeError, TypeError):
                # Fallback to plain string
                value = action_value.strip().lower()
                delay = 0

            if value not in ['on', 'off']:
                logger.error(f"Invalid action value: {value}. Expected 'on' or 'off'.")
                return

            p100 = PyP100.P100(self.ip_address, self.tapo_account_email, self.tapo_account_password)
            p100.handshake()
            p100.login()

            if value == 'on':
                p100.turnOn()
                if delay > 0:
                    p100.turnOffWithDelay(delay)
            else:
                p100.turnOff()
                if delay > 0:
                    p100.turnOnWithDelay(delay)

        except Exception as e:
            logger.error(f"Failed to control smart plug with value '{action_value}': {e}")

    def run(self, action_value):
        try:
            asyncio.run(self.control_smart_plug(action_value=str(action_value).strip().lower()))
        except Exception as e:
            logger.error(f"Exception during smart plug control: {e}")