from django.db import models
from django.utils import timezone

# Create your models here.
class Recipe(models.Model):
    name = models.CharField(max_length=50 )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    var1 = models.FloatField()
    var2 = models.IntegerField()
    var3 = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} . {self.created_at}"

    class Meta:
        ordering = ['-created_at']

class Trends(models.Model):
    id_var = models.IntegerField(null=True, blank=True)
    value = models.FloatField()
    timestamp = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['id_var']),
        ]

    def __str__(self):
        return f"{self.id_var}: {self.value} @ {self.timestamp}"
    
    def to_list(self):
        return [self.id_var, self.value, self.timestamp.replace(second=0, microsecond=0)]
    
class Message(models.Model):
    id_message = models.IntegerField(null=True, blank=True)
    message = models.CharField(max_length=50)
    timestamp = models.DateTimeField()   

    class Meta:
        indexes = [
            models.Index(fields=['timestamp'])
        ]

    def __str__(self):
        return f"{self.message} @ {self.timestamp}"
    
    def to_list(self):
        return [self.message, self.timestamp.replace(second=0, microsecond=0)]