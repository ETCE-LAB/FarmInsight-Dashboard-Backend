
from farminsight_dashboard_backend.models import ActionTrigger
from farminsight_dashboard_backend.services.trigger.base_trigger_handlers import BaseTriggerHandler
from farminsight_dashboard_backend.services.trigger.interval_trigger_handler import IntervalTriggerHandler
from farminsight_dashboard_backend.services.trigger.manual_trigger_handler import ManualTriggerHandler
from farminsight_dashboard_backend.services.trigger.measurement_trigger_handler import MeasurementTriggerHandler
from farminsight_dashboard_backend.services.trigger.time_of_day_trigger_handler import TimeOfDayTriggerHandler
from farminsight_dashboard_backend.services.trigger.forecast_trigger_handler import ForecastTriggerHandler


class TriggerHandlerFactory:
    handlers = {
        "manual": ManualTriggerHandler,
        "timeOfDay": TimeOfDayTriggerHandler,
        "sensorValue": MeasurementTriggerHandler,
        "interval": IntervalTriggerHandler,
        "forecast": ForecastTriggerHandler,
    }

    @staticmethod
    def get_handler(trigger: ActionTrigger) -> BaseTriggerHandler:
        handler_class = TriggerHandlerFactory.handlers.get(trigger.type)
        if not handler_class:
            raise NotImplementedError(f"No handler found for trigger type: {trigger.type}")
        return handler_class(trigger)
