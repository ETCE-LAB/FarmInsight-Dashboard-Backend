import json
import asyncio

from farmbot import Farmbot

from farminsight_dashboard_backend.utils import get_logger
from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


logger = get_logger()

class FarmbotSequenceActionScript(TypedSensor):
    server = None
    email = None
    password = None
    sequence_name = None
    maximumDurationInSeconds = 0

    def init_additional_information(self):
        logger.info("Initializing Farmbot sequence action script.")
        self.maximumDurationInSeconds = self.controllable_action.maximumDurationSeconds or 0

        try:
            additional_information = json.loads(self.controllable_action.additionalInformation or "{}")
        except Exception as e:
            logger.error(f"Failed to parse additionalInformation JSON: {e}", extra={'resource_id': self.controllable_action.id})
            additional_information = {}

        if not isinstance(additional_information, dict):
            logger.error(
                f"Invalid additionalInformation format for action {self.controllable_action.id}: "
                f"{self.controllable_action.additionalInformation}",
                extra={'resource_id': self.controllable_action.id}
            )
            additional_information = {}

        self.server = additional_information.get('server')
        self.sequence_name = additional_information.get('sequence_name')
        self.email = additional_information.get('email')
        self.password = additional_information.get('password')
        logger.info(f"Farmbot action script initialized for server: {self.server} and sequence: {self.sequence_name}")

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='1ff768e0-fa06-4c7e-85b9-a1a40a34bc98',
            name='Farmbot Watering',
            description=("Runs the given sequence of the farmbot. Farmbot sequences will interrupt each other. If you want to avoid this, give an according maximumDurationSeconds. This will prevent any other sequences to be run after an execution for the given time."
                         ";Führt die genannte Sequenz des Farmbots aus. Farmbot Sequenzen unterbrechen sich gegenseitig. Wenn dies vermieden werden möchte, muss eine entsprechende maximale Dauer in Sekunden konfiguriert werden. Dies verhindert dass andere Sequenzen nach dem Start der Sequenz in der gegebenen Zeit ausgeführt werden."),
            action_values=[],
            fields=[
                FieldDescription(
                    id='server',
                    name='Https server;HTTPS Server',
                    description="HTTPS server of the farmbot.;HTTP Endpunkt des Farmbots.",
                    type=FieldType.STRING,
                    rules=[
                        ValidHttpEndpointRule(),
                    ],
                    defaultValue="https://my.farm.bot"
                ),
                FieldDescription(
                    id='sequence_name',
                    name='Sequence name;Sequenzname',
                    description="Sequence name to be executed. Has to be the name - not the sequence_id.;Sequenzname die ausgeführt wird. Muss der Sequenzname sein - nicht die Sequenz_id",
                    type=FieldType.STRING,
                    rules=[],
                ),
                FieldDescription(
                    id='email',
                    name='Email of the farmbot account;Email des Farmbot Accounts',
                    description="Email for the authorization.;Email für die Autorisierung.",
                    type=FieldType.STRING,
                    rules=[],
                ),
                FieldDescription(
                    id='password',
                    name='Password of the farmbot account;Passwort des Farmbot Accounts',
                    description="Password for the authorization.;Passwort für die Autorisierung.",
                    type=FieldType.STRING,
                    rules=[],
                )
            ]
        )

    async def run_sequence(self):
        """
        Executes the Farmbot given farmbot sequence.
        """
        try:
            logger.info(f"Executing Farmbot sequence: '{self.sequence_name}' on server: {self.server}")
            fb = Farmbot()
            logger.info("Acquiring Farmbot token...")
            token = fb.get_token(self.email, self.password, self.server)
            fb.set_token(token)
            logger.info("Token acquired. Executing sequence.")

            fb.sequence(self.sequence_name)
            logger.info(f"Successfully triggered Farmbot sequence: '{self.sequence_name}'")

        except Exception as e:
            logger.error(f"Exception during Farmbot sequence execution: {e}", extra={'resource_id': self.controllable_action.id})

    def run(self, action_value):
        try:
            logger.info(f"Running Farmbot sequence action for sequence: {self.sequence_name}")
            asyncio.run(self.run_sequence())
        except Exception as e:
            logger.error(f"Exception during Farmbot sequence run: {e}", extra={'resource_id': self.controllable_action.id})
