import threading
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.db import models

from farminsight_dashboard_backend.models import FPF, Sensor, ControllableAction, ActionQueue, ActionTrigger, EnergyConsumer
from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
from farminsight_dashboard_backend.services.energy_decision_services import evaluate_energy_state, EnergyAction
from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued
from farminsight_dashboard_backend.services.energy_consumer_services import (
    get_energy_consumer_by_id,
    shutdown_consumer as shutdown_consumer_service
)
from farminsight_dashboard_backend.services.energy_source_services import (
    connect_grid,
    disconnect_grid
)
from farminsight_dashboard_backend.action_scripts.grid_connection_action_script import GridConnectionActionScript
from farminsight_dashboard_backend.utils import get_logger

logger = get_logger()

class EnergyManagementScheduler:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __new__(cls, *args, **kwargs):
        return super(EnergyManagementScheduler, cls).__new__(cls)

    def __init__(self):
        if not getattr(self, "_initialized", False):
            self._scheduler = BackgroundScheduler()
            self.log = get_logger()
            self._initialized = True

    def start(self, interval_seconds: int = 60):
        """
        Start the energy management scheduler.
        Checks energy state every minute by default.
        """
        self._scheduler.add_job(
            self._check_energy_states,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id="energy_management_check",
            replace_existing=True,
            next_run_time=timezone.now() + timedelta(seconds=5)
        )
        self._scheduler.start()
        self.log.info(f"EnergyManagementScheduler started with interval: {interval_seconds} seconds.")

    def _check_energy_states(self):
        """
        Iterate over all active FPFs, check their battery level, and execute necessary actions.
        """
        active_fpfs = FPF.objects.all() # Assuming all FPFs might have energy management

        influx = InfluxDBManager.get_instance()

        for fpf in active_fpfs:
            try:
                # 1. Find the battery level sensor
                # Heuristic: Look for a sensor with 'battery' in name or parameter
                battery_sensor = Sensor.objects.filter(
                    FPF=fpf,
                    isActive=True
                ).filter(
                    models.Q(name__icontains='battery') |
                    models.Q(parameter__icontains='battery')
                ).first()

                if not battery_sensor:
                    # self.log.debug(f"No battery sensor found for FPF {fpf.name}. Skipping energy check.")
                    continue

                # 2. Get latest battery level from InfluxDB
                measurements = influx.fetch_latest_sensor_measurements(
                    fpf_id=str(fpf.id),
                    sensor_ids=[str(battery_sensor.id)]
                )

                latest_data = measurements.get(str(battery_sensor.id))
                if not latest_data:
                    self.log.warning(f"No battery data found for FPF {fpf.name} (Sensor: {battery_sensor.name})")
                    continue

                battery_level_wh = float(latest_data['value'])

                # 3. Evaluate Energy State
                state = evaluate_energy_state(str(fpf.id), battery_level_wh)

                self.log.info(f"Energy Check FPF {fpf.name}: Battery {state.battery_percentage:.1f}% - Action: {state.action.value}")

                # 4. Execute Actions
                if state.action == EnergyAction.CONNECT_GRID:
                    self._trigger_grid_connection(fpf, connect=True)

                elif state.action == EnergyAction.DISCONNECT_GRID:
                    self._trigger_grid_connection(fpf, connect=False)

                elif state.action in [EnergyAction.SHUTDOWN_NON_CRITICAL, EnergyAction.EMERGENCY_SHUTDOWN]:
                    # Ensure grid is connected first if critical
                    self._trigger_grid_connection(fpf, connect=True)

                    # Shutdown consumers
                    for consumer_id in state.consumers_to_shutdown:
                        self._shutdown_consumer(consumer_id)

            except Exception as e:
                self.log.error(f"Error in energy management for FPF {fpf.name}: {e}")

    def _trigger_grid_connection(self, fpf: FPF, connect: bool = True):
        """
        Control grid connection for the FPF.
        First tries to use the linked controllableAction on the grid EnergySource.
        Falls back to the legacy GridConnectionActionScript if no linked action.
        """
        fpf_id = str(fpf.id)

        # Try the new approach: use linked controllableAction on grid source
        if connect:
            if connect_grid(fpf_id):
                self.log.info(f"Grid connected for FPF {fpf.name} via linked action")
                return
        else:
            if disconnect_grid(fpf_id):
                self.log.info(f"Grid disconnected for FPF {fpf.name} via linked action")
                return

        # Fallback: Legacy approach using GridConnectionActionScript
        self._trigger_grid_connection_legacy(fpf, "Connect" if connect else "Disconnect")

    def _trigger_grid_connection_legacy(self, fpf: FPF, action_value: str):
        """
        Legacy method: Find the Grid Connection action by actionClassId.
        """
        grid_action_desc = GridConnectionActionScript.get_description()
        
        grid_action = ControllableAction.objects.filter(
            FPF=fpf,
            isActive=True,
            actionClassId=grid_action_desc.action_script_class_id
        ).first()

        if not grid_action:
            self.log.warning(f"No Grid Connection action found for FPF {fpf.name}")
            return

        self._enqueue_action(grid_action, action_value)

    def _shutdown_consumer(self, consumer_id: str):
        """
        Turn off a specific consumer using its linked controllable action.
        Falls back to name-based matching if no link exists.
        """
        try:
            consumer = get_energy_consumer_by_id(consumer_id)

            # Try the new approach: use linked controllableAction
            if consumer.controllableAction:
                if shutdown_consumer_service(consumer):
                    self.log.info(f"Consumer {consumer.name} shutdown via linked action")
                    return

            # Fallback: Try to find a matching ControllableAction by name
            action = ControllableAction.objects.filter(
                FPF=consumer.FPF,
                name=consumer.name,
                isActive=True
            ).first()
            
            if action:
                self._enqueue_action(action, "Off")
            else:
                self.log.warning(f"No ControllableAction found for EnergyConsumer {consumer.name}")

        except Exception as e:
            self.log.error(f"Error shutting down consumer {consumer_id}: {e}")

    def _enqueue_action(self, action: ControllableAction, value: str):
        """
        Enqueue an action if not already enqueued.
        """
        # Create a manual trigger for now, or maybe we need a 'system' trigger type?
        # Using 'manual' for simplicity as per existing types usually.
        
        # Check if already enqueued to avoid spam
        # We need a trigger ID, but we are creating a new trigger on the fly?
        # Usually we create an ActionTrigger first?
        # Or we just create an ActionQueue entry directly?
        # ActionQueue requires a trigger.
        
        # Let's create a temporary system trigger or reuse one?
        # Better: Create a new ActionTrigger of type 'system' or 'auto'?
        # Let's look at ActionTrigger model.
        
        try:
            # Create a transient trigger for this event
            trigger = ActionTrigger.objects.create(
                name=f"Energy Management: {value}",
                type="auto", # or system
                actionValue=value,
                action=action,
                isActive=True
            )
            
            if not is_already_enqueued(trigger.id):
                ActionQueue.objects.create(
                    action=action,
                    trigger=trigger
                )
                self.log.info(f"Enqueued {action.name} -> {value}")
            
        except Exception as e:
            self.log.error(f"Failed to enqueue action {action.name}: {e}")
