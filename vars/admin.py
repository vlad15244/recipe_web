from django.contrib import admin

from .models import Recipe, Trends, Message

admin.site.register(Recipe)
admin.site.register(Trends)
admin.site.register(Message)
# Register your models here.
