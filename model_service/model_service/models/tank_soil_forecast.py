# model_service/model_service/models.py
import uuid
from django.db import models


class TankSoilForecast(models.Model):
    """
    Hält die Eingabeparameter und (optional) das Ergebnis der Berechnung.
    'result' ist ein freies JSON, z. B. die DataFrame-Zeilen (Liste von Dicts)
    oder eine Summary (du kannst das je nach Bedarf befüllen).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    latitude = models.DecimalField(max_digits=8, decimal_places=5)    # z.B. 51.90000
    longitude = models.DecimalField(max_digits=8, decimal_places=5)   # z.B. 10.42000
    forecast_days = models.PositiveSmallIntegerField()

    tank_capacity = models.PositiveIntegerField()
    soil_taw_mm = models.FloatField()
    soil_p = models.FloatField()
    kc = models.FloatField()
    irrig_eff = models.FloatField()
    rain_off = models.FloatField()
    irrigation_area_m2 = models.FloatField()
    soil_init_ratio = models.FloatField()
    irrigation_event_l = models.FloatField()

    # optionales Ergebnis der Berechnung (z. B. What-if-Plan oder Kurve)
    result = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "model_service_forecast_run"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ForecastRun({self.latitude},{self.longitude},days={self.forecast_days})"
