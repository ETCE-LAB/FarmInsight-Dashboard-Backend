from django.contrib import admin

'''
from django.apps import apps

app = apps.get_app_config('farminsight_dashboard_backend')

for model_name, model in app.models.items():
    admin.site.register(model)
    
'''

from farminsight_dashboard_backend.models import Userprofile, LogMessage

admin.site.register(Userprofile)
admin.site.register(LogMessage)
