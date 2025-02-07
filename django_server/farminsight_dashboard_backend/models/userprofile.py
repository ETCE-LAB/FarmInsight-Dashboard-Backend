from farminsight_dashboard_backend.utils import ListableEnum

from django.db import models
from django.contrib.auth.models import AbstractUser

class SystemRole(ListableEnum):
    SystemAdmin = 'sysAdmin'
    User = 'user'


class Userprofile(AbstractUser):
    name = models.CharField(max_length=256)
    systemRole = models.CharField(max_length=256, default=SystemRole.User.value)

    def __str__(self):
        return f"{self.email} {self.name} - {self.systemRole}"
