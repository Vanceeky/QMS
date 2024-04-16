from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(Route)
admin.site.register(Station)
admin.site.register(JeepneyDriver)
admin.site.register(QueueEntry)