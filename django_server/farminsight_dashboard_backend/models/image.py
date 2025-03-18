import uuid
from django.db import models
from django.utils import timezone
from .camera import Camera


class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    measuredAt = models.DateTimeField(default=timezone.now)
    image = models.ImageField(upload_to='images/')
    camera = models.ForeignKey(Camera, related_name='images', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.camera.name} {self.measuredAt} {self.camera}"
