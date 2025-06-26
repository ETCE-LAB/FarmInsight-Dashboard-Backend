import json
import asyncio

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor
from plugp100.common.credentials import AuthCredential
from plugp100.new.device_factory import connect, DeviceConnectConfiguration
from plugp100.new.components.on_off_component import OnOffComponent


logger = get_logger()


class TapoP100SmartPlugActionScriptWithDelay(TypedSensor):
    ip_address = None
    tapo_account_email = None
    tapo_account_password = None
    maximumDurationInSeconds = 0

    def init_additional_information(self):
        self.maximumDurationInSeconds = self.controllable_action.maximumDurationSeconds or 0
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.ip_address = additional_information['ip-address']
        self.tapo_account_email = additional_information['tapo-account-email']
        self.tapo_account_password = additional_information['tapo-account-password']

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='dc83813b-1541-4aac-8caa-ba448a6bbdda',
            name='Tapo Smart Plug (HTTP)',
            description="Turns a Tapo Smart Plug via HTTP calls on and off. MaximumDurationInSeconds adds a delay (optional) to reset the command after the specified time.;Kontrolliert einen Tapo Smart Plug via HTTP-Anfrage. MaximumDurationInSeconds kann optional genutzt werden um den Befehl nach angegebener Zeit zurückzusetzen.",
            action_values=['On', 'Off'],
            fields=[
                FieldDescription(
                    id='ip-address',
                    name='IP Address;IP Adresse',
                    description="IP address of the Tapo smart plug.;IP Adresse vom Tapo Smart Plug.",
                    type=FieldType.STRING,
                    rules=[]
                ),
                FieldDescription(
                    id='tapo-account-email',
                    name='Tapo Account Email;Tapo Konto Email',
                    description="Tapo account email.;Tapo Konto Email.",
                    type=FieldType.STRING,
                    rules=[]
                ),
                FieldDescription(
                    id='tapo-account-password',
                    name='Tapo Account Password;Tapo Konto Passwort',
                    description="Tapo account password.;Tapo Konto Passwort.",
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
            """
        try:

            if action_value not in ['on', 'off']:
                raise RuntimeError(f"Invalid action value: {action_value}. Expected 'on' or 'off'.")


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

            power = OnOffComponent(device.client)
            await power.update(device.raw_state)

            if action_value == 'on':
                await power.turn_on()
            elif action_value == 'off':
                await power.turn_off()

        except Exception as e:
            raise RuntimeError(f"Failed to control smart plug with value '{action_value}': {e}")

    def run(self, action_value):
        try:
            asyncio.run(self.control_smart_plug(action_value=str(action_value).strip().lower()))
        except Exception as e:
            raise RuntimeError(f"Exception during smart plug control: {e}")