from django.db import models
from django.contrib.auth.models import User
import uuid
import random

def generate_short_id():
    # Generate a random 4-digit numeric ID
    return str(random.randint(1000, 9999))

# Create your models here.

class Station(models.Model):
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100, null=True, blank=True)
    station_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    routes = models.ManyToManyField('Route', related_name='stations')

    def __str__(self):
        return f"{self.name} - {self.station_manager}"

class Route(models.Model):
    from_route = models.CharField(max_length=100)
    to_route = models.CharField(max_length=100)
    description = models.TextField(null = True, blank = True)

    def __str__(self):
        return f"{self.from_route} to {self.to_route}"
    

class JeepneyDriver(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    address = models.TextField()
    contact_number = models.CharField(max_length=20)

    route = models.ForeignKey(Route, on_delete=models.SET_NULL,  max_length=50, null=True, blank=True)

    photo = models.ImageField(upload_to='driver_photo', blank=True, null=True)

    qr_code = models.ImageField(upload_to='driver_qrcodes', blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    



class QueueEntry(models.Model):
    STATUS_CHOICES = (
        ('serving', 'Now Serving'),
        ('waiting', 'Waiting'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    )
    token_number = models.CharField(primary_key=True, default=generate_short_id, unique=True, editable=False, max_length=4)
    driver = models.ForeignKey(JeepneyDriver, on_delete=models.CASCADE)
    entry_time = models.DateTimeField(auto_now_add=True)
    created = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, null=True, blank=True)

    station = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created']

    def __str__(self):
        return f"{self.token_number} - {self.driver.first_name} {self.driver.last_name}"