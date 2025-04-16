import uuid
from django.db import models
from .organization import Organization


class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    latitude = models.FloatField()
    longitude = models.FloatField()
    city = models.CharField(max_length=64)
    street = models.CharField(max_length=64)
    houseNumber = models.CharField(max_length=16)
    gatherForecasts = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['organization', 'name'], name='unique_location_name_per_organization')
        ]

    def __str__(self):
        return f"{self.organization.name}: {self.name} lat: {self.latitude} long: {self.longitude} {self.street} {self.houseNumber}, {self.city}"
