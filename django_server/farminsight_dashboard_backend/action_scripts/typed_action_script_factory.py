from typing import Type

from farminsight_dashboard_backend.action_scripts.typed_action_script import TypedSensor


def all_subclasses(cls):
    # Required to also handle deeper subclasses!
    return set(cls.__subclasses__()).union(
        [s for c in cls.__subclasses__() for s in all_subclasses(c)])

class TypedActionScriptFactory:
    registry = None

    def __init__(self, **kwargs):
        if self.registry is None:
            self.registry = {}
            for action_script_class in all_subclasses(TypedSensor):
                description = action_script_class.get_description()
                if description.action_script_class_id in self.registry:
                    raise Exception("Multiple typed action scripts with the same id detected!!")

                self.registry[description.action_script_class_id] = action_script_class

    def get_available_action_scripts(self) -> list[str]:
        return [
            action_script_class.get_description() for action_script_class in self.registry.values()
        ]

    #def get_typed_action_script(self, sensor_model: SensorConfig) -> TypedSensor:
    #    return self.registry[str(sensor_model.sensorClassId)](sensor_model)

    def get_typed_action_script_class(self, action_script_class_id: str) -> Type[TypedSensor]:
        return self.registry[action_script_class_id]
