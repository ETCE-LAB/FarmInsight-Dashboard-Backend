import json
import asyncio
from plugp100.common.credentials import AuthCredential
from plugp100.new.device_factory import connect, DeviceConnectConfiguration
from farminsight_dashboard_backend.utils import get_logger
from plugp100.new.components.on_off_component import OnOffComponent

from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


logger = get_logger()

class TapoP100SmartPlugActionScript(TypedSensor):
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
            action_script_class_id='c246ba66-992b-40b4-bb2f-fa55e55d169c',
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
                ),
            ]
        )

    async def control_smart_plug(self, action_value):
        """
        Controls the smart plug by turning it on or off.
        :param action_value:
        :return:
        """
        credentials = AuthCredential(self.tapo_account_email, self.tapo_account_password)

        device_configuration = DeviceConnectConfiguration(
            host=self.ip_address,
            credentials=credentials,
            device_type="SMART.TAPOPLUG",
            encryption_type="klap",
            encryption_version=2
        )

        device = await connect(device_configuration)
        await device.update()

        # Create OnOffComponent with the internal TapoClient
        power = OnOffComponent(device.client)
        await power.update(device.raw_state)

        if action_value == 'on':
            await power.turn_on()
        elif action_value == 'off':
            await power.turn_off()
        else:
            logger.error(f"Not a valid action value. Allowed values are 'On' and 'Off', but is: {action_value}")


    def run(self, action_value):
        try:
            asyncio.run(self.control_smart_plug(action_value=str(action_value).strip().lower()))
        except Exception as e:
            logger.error(f"Exception during smart plug control: {e}")

