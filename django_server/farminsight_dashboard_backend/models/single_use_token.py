from django.db import models

from farminsight_dashboard_backend.models import Userprofile


class SingleUseToken(models.Model):
    token = models.CharField(max_length=255, unique=True)
    valid_until = models.DateTimeField()
    user = models.ForeignKey(Userprofile, blank=True, null=True, on_delete=models.CASCADE)
