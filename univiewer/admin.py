# -*- coding: utf-8 -*-


from django.contrib.gis import admin
from .models import parcel, market_value_analysis

admin.site.register(parcel)
admin.site.register(market_value_analysis)


# Register your models here.
