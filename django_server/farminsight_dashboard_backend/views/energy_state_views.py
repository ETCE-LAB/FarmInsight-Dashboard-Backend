from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from farminsight_dashboard_backend.models import FPF, ControllableAction, ActionTrigger, ActionQueue, EnergyConsumer
from farminsight_dashboard_backend.services.energy_decision_services import (
    get_energy_state_summary,
    evaluate_energy_state,
    should_connect_grid,
    estimate_runtime_hours,
    get_fpf_energy_config,
    EnergyAction
)
from farminsight_dashboard_backend.services.energy_consumer_services import (
    get_energy_consumers_by_fpf_id,
    get_total_consumption_by_fpf_id
)
from farminsight_dashboard_backend.services.energy_source_services import (
    get_energy_sources_by_fpf_id,
    get_total_available_power_by_fpf_id,
    get_current_power_output_by_fpf_id
)
from farminsight_dashboard_backend.services.action_queue_services import is_already_enqueued, process_action_queue
from farminsight_dashboard_backend.action_scripts.grid_connection_action_script import GridConnectionActionScript
from farminsight_dashboard_backend.serializers.energy_consumer_serializer import EnergyConsumerDetailSerializer
from farminsight_dashboard_backend.serializers.energy_source_serializer import EnergySourceSerializer, EnergySourceDetailSerializer
from farminsight_dashboard_backend.utils import get_logger


logger = get_logger()


def _get_or_create_energy_trigger(action: ControllableAction, trigger_name: str, action_value: str) -> ActionTrigger:
    """
    Get or create an energy management trigger for the given action.
    Reuses existing triggers to avoid database spam.
    """
    trigger = ActionTrigger.objects.filter(
        action=action,
        type="auto",
        actionValue=action_value,
        name=trigger_name
    ).first()

    if not trigger:
        trigger = ActionTrigger.objects.create(
            name=trigger_name,
            type="auto",
            actionValueType="string",
            actionValue=action_value,
            triggerLogic="",
            description=f"Automatic energy management trigger for {action.name}",
            action=action,
            isActive=True
        )

    return trigger


def _execute_energy_action(fpf_id: str, state) -> dict:
    """
    Execute the recommended energy action by enqueueing appropriate actions.
    
    :param fpf_id: UUID of the FPF
    :param state: EnergyState object with recommended action
    :return: Dictionary with execution details
    """
    execution_result = {
        "actions_queued": [],
        "errors": []
    }
    
    try:
        fpf = FPF.objects.get(id=fpf_id)
    except FPF.DoesNotExist:
        execution_result["errors"].append(f"FPF {fpf_id} not found")
        return execution_result
    
    # Handle grid connection actions
    if state.action in [EnergyAction.CONNECT_GRID, EnergyAction.SHUTDOWN_NON_CRITICAL, EnergyAction.EMERGENCY_SHUTDOWN]:
        # Find the Grid Connection action
        grid_action_desc = GridConnectionActionScript.get_description()
        grid_action = ControllableAction.objects.filter(
            FPF=fpf,
            isActive=True,
            actionClassId=grid_action_desc.action_script_class_id
        ).first()
        
        if grid_action:
            try:
                trigger = _get_or_create_energy_trigger(
                    grid_action,
                    "Energy Management: Connect Grid",
                    "Connect"
                )
                if not is_already_enqueued(trigger.id):
                    ActionQueue.objects.create(action=grid_action, trigger=trigger)
                    execution_result["actions_queued"].append(f"Grid connection: Connect")
                    logger.info(f"Queued grid connection for FPF {fpf.name}")
            except Exception as e:
                execution_result["errors"].append(f"Failed to queue grid connection: {str(e)}")
        else:
            execution_result["errors"].append("No Grid Connection action configured for this FPF")
    
    elif state.action == EnergyAction.DISCONNECT_GRID:
        # Disconnect from grid
        grid_action_desc = GridConnectionActionScript.get_description()
        grid_action = ControllableAction.objects.filter(
            FPF=fpf,
            isActive=True,
            actionClassId=grid_action_desc.action_script_class_id
        ).first()
        
        if grid_action:
            try:
                trigger = _get_or_create_energy_trigger(
                    grid_action,
                    "Energy Management: Disconnect Grid",
                    "Disconnect"
                )
                if not is_already_enqueued(trigger.id):
                    ActionQueue.objects.create(action=grid_action, trigger=trigger)
                    execution_result["actions_queued"].append(f"Grid connection: Disconnect")
                    logger.info(f"Queued grid disconnection for FPF {fpf.name}")
            except Exception as e:
                execution_result["errors"].append(f"Failed to queue grid disconnection: {str(e)}")
    
    # Handle consumer shutdowns
    if state.action in [EnergyAction.SHUTDOWN_NON_CRITICAL, EnergyAction.EMERGENCY_SHUTDOWN]:
        for consumer_id in state.consumers_to_shutdown:
            try:
                consumer = EnergyConsumer.objects.get(id=consumer_id)
                # Find matching ControllableAction by name
                consumer_action = ControllableAction.objects.filter(
                    FPF=fpf,
                    name=consumer.name,
                    isActive=True
                ).first()
                
                if consumer_action:
                    trigger = _get_or_create_energy_trigger(
                        consumer_action,
                        f"Energy Management: Shutdown {consumer.name}",
                        "Off"
                    )
                    if not is_already_enqueued(trigger.id):
                        ActionQueue.objects.create(action=consumer_action, trigger=trigger)
                        execution_result["actions_queued"].append(f"Shutdown: {consumer.name}")
                        logger.info(f"Queued shutdown for consumer {consumer.name}")
            except Exception as e:
                execution_result["errors"].append(f"Failed to shutdown consumer {consumer_id}: {str(e)}")
    
    # Process the action queue
    if execution_result["actions_queued"]:
        try:
            process_action_queue()
        except Exception as e:
            logger.error(f"Error processing action queue: {e}")
    
    return execution_result


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_energy_state(request, fpf_id: str):
    """
    Get the current energy state for an FPF.

    Query Parameters:
    - battery_level_wh: Current battery level in Wh (required)

    Returns energy state with recommended actions.
    """
    battery_level_str = request.query_params.get('battery_level_wh')

    if not battery_level_str:
        return Response(
            {"error": "Missing required parameter: battery_level_wh"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        battery_level_wh = float(battery_level_str)
    except ValueError:
        return Response(
            {"error": "battery_level_wh must be a valid number"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        energy_state = get_energy_state_summary(fpf_id, battery_level_wh)
        return Response(energy_state, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error getting energy state for FPF {fpf_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_energy_dashboard(request, fpf_id: str):
    """
    Get complete energy dashboard data for an FPF.

    Query Parameters:
    - battery_level_wh: Current battery level in Wh (optional, defaults to 50% of FPF's battery max)
    - include_graph_data: Whether to include graph data with forecasts (optional, default: true)
    - hours_back: Hours of historical data for graph (optional, default: 12)
    - hours_ahead: Hours of forecast data for graph (optional, default: 24)

    Returns combined view of consumers, sources, current state, and graph data with forecasts.
    """
    from farminsight_dashboard_backend.services.energy_forecast_services import get_energy_graph_data

    # Get FPF-specific energy configuration
    config = get_fpf_energy_config(fpf_id)
    default_battery = config['battery_max_wh'] * 0.5
    
    battery_level_str = request.query_params.get('battery_level_wh', str(default_battery))
    include_graph_data = request.query_params.get('include_graph_data', 'true').lower() == 'true'
    hours_back = int(request.query_params.get('hours_back', '12'))
    hours_ahead = int(request.query_params.get('hours_ahead', '24'))

    try:
        battery_level_wh = float(battery_level_str)
    except ValueError:
        battery_level_wh = default_battery

    try:
        # Get all data
        consumers = get_energy_consumers_by_fpf_id(fpf_id)
        sources = get_energy_sources_by_fpf_id(fpf_id)
        energy_state = get_energy_state_summary(fpf_id, battery_level_wh)
        runtime_hours = estimate_runtime_hours(fpf_id, battery_level_wh)

        response_data = {
            "fpf_id": fpf_id,
            "consumers": {
                "list": EnergyConsumerDetailSerializer(consumers, many=True).data,
                "total_consumption_watts": get_total_consumption_by_fpf_id(fpf_id),
                "count": len(consumers)
            },
            "sources": {
                "list": EnergySourceDetailSerializer(sources, many=True).data,
                "total_available_watts": get_total_available_power_by_fpf_id(fpf_id),
                "current_output_watts": get_current_power_output_by_fpf_id(fpf_id),
                "count": len(sources)
            },
            "state": energy_state,
            "estimated_runtime_hours": runtime_hours if runtime_hours != float('inf') else None,
            "thresholds": {
                "grid_connect_percent": config['grid_connect_threshold'],
                "shutdown_percent": config['shutdown_threshold'],
                "warning_percent": config['warning_threshold'],
                "grid_disconnect_percent": config['grid_disconnect_threshold'],
                "battery_max_wh": config['battery_max_wh']
            }
        }

        # Include graph data with forecasts if requested
        if include_graph_data:
            response_data["graph_data"] = get_energy_graph_data(fpf_id, hours_back, hours_ahead)

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting energy dashboard for FPF {fpf_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def evaluate_energy_action(request, fpf_id: str):
    """
    Evaluate and optionally execute energy management action.

    Request Body:
    - battery_level_wh: Current battery level in Wh (required)
    - execute: Whether to execute the recommended action (optional, default: false)

    Returns recommended action and execution status.
    """
    battery_level_wh = request.data.get('battery_level_wh')
    execute = request.data.get('execute', False)

    if battery_level_wh is None:
        return Response(
            {"error": "Missing required field: battery_level_wh"},
            status=status.HTTP_400_BAD_REQUEST
        )


    try:
        battery_level_wh = float(battery_level_wh)
    except ValueError:
        return Response(
            {"error": "battery_level_wh must be a valid number"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        state = evaluate_energy_state(fpf_id, battery_level_wh)

        response_data = {
            "action": state.action.value,
            "status": state.status,
            "message": state.message,
            "battery_percentage": round(state.battery_percentage, 2),
            "grid_connected": state.grid_connected,
            "consumers_to_shutdown": [str(c) for c in state.consumers_to_shutdown],
            "executed": False
        }

        if execute:
            # Execute the recommended action via ActionQueue
            execution_result = _execute_energy_action(fpf_id, state)
            logger.info(
                f"Energy action '{state.action.value}' executed for FPF {fpf_id}",
                extra={'resource_id': fpf_id}
            )
            response_data["executed"] = True
            response_data["actions_queued"] = execution_result["actions_queued"]
            response_data["execution_errors"] = execution_result["errors"]
            
            if execution_result["actions_queued"]:
                response_data["execution_message"] = f"Queued {len(execution_result['actions_queued'])} action(s) for execution."
            elif execution_result["errors"]:
                response_data["execution_message"] = f"Failed to queue actions: {', '.join(execution_result['errors'])}"
            else:
                response_data["execution_message"] = "No actions needed for current state."

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error evaluating energy action for FPF {fpf_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_battery_state(request, fpf_id: str):
    """
    Get the current battery state for an FPF.
    Fetches live data from the battery sensor if available.

    Returns:
        - battery_level_wh: Current battery level in Wh
        - percentage: Battery percentage (0-100)
        - last_updated: Timestamp of last measurement
        - source_name: Name of the battery source
    """
    from farminsight_dashboard_backend.models import EnergySource
    from farminsight_dashboard_backend.services.influx_services import InfluxDBManager
    from farminsight_dashboard_backend.services.energy_decision_services import get_fpf_energy_config

    try:
        # Get FPF configuration for battery max
        config = get_fpf_energy_config(fpf_id)
        battery_max_wh = config['battery_max_wh']

        # Find battery source for this FPF
        battery_source = EnergySource.objects.filter(
            FPF_id=fpf_id,
            sourceType='battery',
            isActive=True
        ).first()

        if not battery_source:
            return Response(
                {"error": "No active battery source found for this FPF"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Try to get live data from linked sensor
        battery_level_wh = None
        last_updated = None

        if battery_source.sensor and battery_source.sensor.isActive:
            try:
                influx = InfluxDBManager.get_instance()
                measurements = influx.fetch_latest_sensor_measurements(
                    fpf_id=fpf_id,
                    sensor_ids=[str(battery_source.sensor.id)]
                )

                sensor_data = measurements.get(str(battery_source.sensor.id))
                if sensor_data and 'value' in sensor_data:
                    battery_level_wh = float(sensor_data['value'])
                    last_updated = sensor_data.get('measuredAt')
            except Exception as e:
                logger.warning(f"Could not fetch live battery data: {e}")

        # Fallback: Try to fetch from BatteryLevel measurement in InfluxDB
        if battery_level_wh is None:
            try:
                influx = InfluxDBManager.get_instance()
                battery_data = influx.fetch_latest_battery_level(fpf_id)
                if battery_data:
                    battery_level_wh = battery_data.get('level_wh')
                    last_updated = battery_data.get('timestamp')
            except Exception as e:
                logger.warning(f"Could not fetch battery level from InfluxDB: {e}")

        # Fallback: Use currentOutputWatts from battery source
        if battery_level_wh is None:
            battery_level_wh = battery_source.currentOutputWatts
            last_updated = battery_source.updatedAt.isoformat() if battery_source.updatedAt else None

        # Calculate percentage
        percentage = min(100.0, max(0.0, (battery_level_wh / battery_max_wh) * 100)) if battery_max_wh > 0 else 0.0

        return Response({
            "battery_level_wh": battery_level_wh,
            "percentage": round(percentage, 2),
            "max_wh": battery_max_wh,
            "last_updated": last_updated,
            "source_name": battery_source.name,
            "source_id": str(battery_source.id)
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error getting battery state for FPF {fpf_id}: {e}")
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
