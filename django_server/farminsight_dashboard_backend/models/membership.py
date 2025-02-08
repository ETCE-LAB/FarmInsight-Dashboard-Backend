import uuid
from django.db import models
from django.utils import timezone
from .userprofile import Userprofile
from .organization import Organization
from farminsight_dashboard_backend.utils import ListableEnum


class MembershipRole(ListableEnum):
    Admin = 'admin'
    Member = 'member'


class Membership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    membershipRole = models.CharField(max_length=256)
    createdAt = models.DateTimeField(default=timezone.now)
    userprofile = models.ForeignKey(Userprofile, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.organization.name}: {self.userprofile.email} -- {self.membershipRole}"
