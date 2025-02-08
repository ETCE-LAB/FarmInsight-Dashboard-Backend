from django.db import models


class SingleUseToken(models.Model):
    token = models.CharField(max_length=255, unique=True)
    valid_until = models.DateTimeField()
