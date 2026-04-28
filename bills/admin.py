from django.contrib import admin
from .models import CustomerProfile, Bill

admin.site.register(CustomerProfile)
admin.site.register(Bill)