import threading
import requests
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone

from farminsight_dashboard_backend.models import ResourceManagementModel, ControllableAction, ActionMapping
from farminsight_dashboard_backend.services.forecast_action_scheduler_services import ForecastActionScheduler
from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
from farminsight_dashboard_backend.services.model_action_injection_services import inject_model_actions_into_queue
from farminsight_dashboard_backend.services.resource_management_model_services import ResourceManagementModelService
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()

class ModelScheduler:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __new__(cls, *args, **kwargs):
        return super(ModelScheduler, cls).__new__(cls)

    def __init__(self):
        """
        Initialize the ResourceForecastScheduler
        """
        if not getattr(self, "_initialized", False):
            self._scheduler = BackgroundScheduler()
            self.log = get_logger()
            self._initialized = True

    def start(self):
        """
        Start the scheduler
        """
        self._add_all_model_jobs()
        self._scheduler.start()
        self.log.info("ResourceForecastScheduler started.")

    def add_model_job(self, model_id: str):
        """
        Add a periodic task for a specific ResourceManagementModel
        """
        try:
            model = ResourceManagementModel.objects.get(id=model_id)
            if not model.isActive:
                self.log.debug(f"Model {model.name} is inactive. Skipping scheduling.")
                return

            interval = model.intervalSeconds or 86400  # default once per day
            job_id = f"resource_model_{model.id}_forecast"

            self._scheduler.add_job(
                self._fetch_and_store_forecast,
                trigger=IntervalTrigger(seconds=interval),
                args=[model.id],
                id=job_id,
                replace_existing=True,
                next_run_time=timezone.now() + timedelta(seconds=5),
                max_instances=1
            )

            self.log.info(f"Scheduled forecast fetch for model '{model.name}' every {interval} seconds.")
        except ResourceManagementModel.DoesNotExist:
            self.log.warning(f"ResourceManagementModel with ID {model_id} does not exist.")

    def remove_model_job(self, model_id: str):
        """
        Remove the forecast task for a specific model
        """
        job_id = f"resource_model_{model_id}_forecast"
        existing_job = self._scheduler.get_job(job_id)
        if existing_job:
            self._scheduler.remove_job(job_id)
            self.log.debug(f"Removed forecast job for model {model_id}.")

    def reschedule_model_job(self, model_id: str, new_interval: int):
        """
        Reschedule forecast task for a specific model with new interval
        """
        self.remove_model_job(model_id)
        self.add_model_job(model_id)

    def _add_all_model_jobs(self):
        """
        Add jobs for all active models
        """
        models = ResourceManagementModel.objects.filter(isActive=True)
        for model in models:
            self.add_model_job(str(model.id))

    def _fetch_and_store_forecast(self, model_id: str):
        """
        Fetch forecast data from model API, store it in InfluxDB,
        and schedule forecast-based actions for the active scenario.
        """
        try:
            model = ResourceManagementModel.objects.get(id=model_id)
            base_url = model.URL.rstrip('/')
            query_params = ResourceManagementModelService.  build_model_query_params(model)
            full_url = f"{base_url}/farm-insight{query_params}"

            response = requests.get(full_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # --- Store forecasts in InfluxDB ---
            influx = InfluxDBManager.get_instance()
            influx.write_model_forecast(
                fpf_id=str(model.FPF.id),
                model_id=str(model.id),
                model_name=model.name,
                forecasts=data
            )
            logger.info(f"Forecasts updated for model {model.name}")

            # --- Handle actions (forecast triggers) ---
            actions = data.get("actions", [])
            if not actions:
                logger.debug(f"No actions found in forecast for model {model.name}.")
                return

            # 1️⃣ Find actions for the active scenario
            # As .lower() changes "-" to "_", we replace them manually here
            active_scenario = (model.activeScenario or "").lower().replace("-", "_")
            scenario_entry = next(
                (
                    a for a in actions
                    if a.get("name", "").lower().replace("-", "_") == active_scenario
                ),
                None
            )
            if not scenario_entry:
                logger.warning(f"No matching scenario '{active_scenario}' found for model {model.name}.")
                return

            scenario_actions = scenario_entry.get("value", [])
            if not scenario_actions:
                logger.warning(f"No action entries found for scenario '{active_scenario}' in model {model.name}.")
                return

            # 2️⃣ Schedule forecast-based actions
            # Each entry looks like {"timestamp": "...", "value": 1.5, "action": "watering"}
            scheduler = ForecastActionScheduler.get_instance()
            for action_entry in scenario_actions:
                action_name = action_entry.get("action")
                if not action_name:
                    continue

                try:
                    mapped_action = ActionMapping.objects.get(
                        action_name=action_name,
                        resource_management_model_id=model_id
                    )
                    print(mapped_action)
                    print("try to get:",mapped_action.controllable_action_id)
                    controllable_action = ControllableAction.objects.get(
                        id=mapped_action.controllable_action_id,
                        isActive=True
                    )

                except ActionMapping.DoesNotExist:
                    logger.warning(f"Unknown or unmapped action '{action_name}' for model {model.name}")
                    continue
                except ControllableAction.DoesNotExist:
                    logger.warning(f"Unknown or inactive controllable action '{action_name}' for model {model.name}")
                    continue

                # The scheduler will manage the chain (next actions)
                scheduler.schedule_forecast_chain(controllable_action, scenario_actions)

            logger.info(f"Scheduled forecast actions for model {model.name} ({active_scenario}).")

        except requests.RequestException as e:
            logger.error(f"Error fetching forecast for model {model_id}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating forecast for model {model_id}: {e}")