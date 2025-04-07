import uuid
from django.db import models


class Hardware(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=256)

    def __str__(self):
        return f"{self.name}"
