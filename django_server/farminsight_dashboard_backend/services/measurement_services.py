from farminsight_dashboard_backend.models import Sensor



def store_measurements_in_influx(sensor_id, data):
    from farminsight_dashboard_backend.services import InfluxDBManager
    sensor = Sensor.objects.get(id=sensor_id)
    InfluxDBManager.get_instance().write_sensor_measurements(fpf_id=str(sensor.FPF_id),
                                                             sensor_id=sensor.id,
                                                             measurements=data)
    # Check for triggers paired to the sensor
    from farminsight_dashboard_backend.services.trigger.measurement_trigger_handler import \
        create_measurement_auto_triggered_actions_in_queue

    last_measurement = data[len(data)-1]['value']
    create_measurement_auto_triggered_actions_in_queue(sensor_id, last_measurement)
