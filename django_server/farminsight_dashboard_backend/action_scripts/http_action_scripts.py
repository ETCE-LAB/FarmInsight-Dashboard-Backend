import json
import requests

from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription, \
    FieldDescription, ValidHttpEndpointRule, FieldType
from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


class PostHttpActionScript(TypedSensor):
    http_endpoint = None

    def init_additional_information(self):
        additional_information = json.loads(self.controllable_action.additionalInformation)
        self.http_endpoint = additional_information['http']

    @staticmethod
    def get_description() -> ActionScriptDescription:
        return ActionScriptDescription(
            action_script_class_id='054513e8-e2f2-473e-b9bd-1e36c9d26889',
            name='HTTP Post',
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

    def run(self, action_value):
        print("request sending for: ", action_value)
        #response = requests.post(self.http_endpoint)
        #response.raise_for_status()
        #return MeasurementResult(value=response.json().get("value"))

