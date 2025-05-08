import json

from farminsight_dashboard_backend.models import ActionTrigger


class MeasurementTriggerManager:
    _sensor_to_triggers = {}

    @classmethod
    def build_trigger_mapping(cls):
        cls._sensor_to_triggers = {}

        triggers = ActionTrigger.objects.filter(isActive=True, type="sensorValue")

        for trigger in triggers:
            logic = json.loads(trigger.triggerLogic)
            # logic could be a single dict or a complex nested one
            sensor_ids = cls.extract_sensor_ids(logic)
            for sensor_id in sensor_ids:
                cls._sensor_to_triggers.setdefault(sensor_id, []).append(trigger.id)

    @classmethod
    def extract_sensor_ids(cls, logic):
        """
        Recursively extracts all sensor IDs from triggerLogic JSON
        """
        sensor_ids = []

        if isinstance(logic, dict):
            if "sensorId" in logic:
                sensor_ids.append(logic["sensorId"])
            if "conditions" in logic:
                for condition in logic["conditions"]:
                    sensor_ids.extend(cls.extract_sensor_ids(condition))
        elif isinstance(logic, list):
            for item in logic:
                sensor_ids.extend(cls.extract_sensor_ids(item))
        return sensor_ids

    @classmethod
    def get_trigger_ids_for_sensor(cls, sensor_id):
        return cls._sensor_to_triggers.get(sensor_id, [])
