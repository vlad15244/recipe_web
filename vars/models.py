from django.db import models
from django.utils import timezone

# Create your models here.
class Recipe(models.Model):
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    var1 = models.FloatField()
    var2 = models.IntegerField()
    var3 = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} . {self.created_at}"

    class Meta:
        ordering = ['-created_at']



