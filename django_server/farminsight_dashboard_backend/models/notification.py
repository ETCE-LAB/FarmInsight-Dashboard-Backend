from django.db import models



class Notification(models.Model):
    room_id = models.TextField(primary_key=True)
    name = models.TextField(blank=False)

