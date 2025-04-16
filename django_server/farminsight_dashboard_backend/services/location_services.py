from farminsight_dashboard_backend.models import Location, Organization

from farminsight_dashboard_backend.exceptions import NotFoundException
from farminsight_dashboard_backend.serializers.location_serializer import LocationSerializer


def create_location(data) -> LocationSerializer:

    try:
        organisation = Organization.objects.get(id=data['organizationId'])
    except Organization.DoesNotExist:
        raise ValueError("Organisation with the given ID does not exist")

    serializer = LocationSerializer(data=data, partial=True)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        if serializer.data['gatherForecasts']:
            # Schedule the weather forecast job
            from farminsight_dashboard_backend.services import WeatherForecastScheduler
            WeatherForecastScheduler.get_instance().add_forecast_job(serializer.data['id'])
        return serializer


def update_location(location_id, data) -> LocationSerializer:
    location = Location.objects.get(id=location_id)
    serializer = LocationSerializer(location, data=data)
    if serializer.is_valid(raise_exception=True):
        serializer.save()
        if serializer.data['gatherForecasts']:

            # Schedule the weather forecast job
            from farminsight_dashboard_backend.services import WeatherForecastScheduler

            WeatherForecastScheduler.get_instance().add_forecast_job(serializer.data['id'])
        else:
            # Remove the job if gathering is disabled
            from farminsight_dashboard_backend.services import WeatherForecastScheduler
            WeatherForecastScheduler.get_instance().remove_forecast_job(serializer.data['id'])
        return serializer


def remove_location(location_id):
    location = Location.objects.get(id=location_id)
    location.delete()


def get_location_by_id(location_id) -> LocationSerializer:
    location = Location.objects.filter(id=location_id).first()
    if location is None:
        raise NotFoundException(f'Location with id: {location_id} was not found.')
    return location


def gather_locations_by_organization_id(organization_id) -> LocationSerializer:
    locations = Location.objects.filter(organization_id=organization_id)
    if locations is None:
        raise NotFoundException(f'Locations with organization id: {organization_id} was not found.')
    return LocationSerializer(locations, many=True)

