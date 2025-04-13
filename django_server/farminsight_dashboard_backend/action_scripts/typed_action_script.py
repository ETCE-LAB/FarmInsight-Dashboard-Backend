from abc import ABC, abstractmethod

from farminsight_dashboard_backend.action_scripts.action_script_description import ActionScriptDescription
from farminsight_dashboard_backend.models import ControllableAction


class TypedSensor(ABC):
    def __init__(self, controllable_action:ControllableAction):
        self.controllable_action = controllable_action
        self.init_additional_information()

    @abstractmethod
    def init_additional_information(self):
        pass

    @staticmethod
    @abstractmethod
    def get_description() -> ActionScriptDescription:
        pass

    @abstractmethod
    def run(self, action_value):
        pass
